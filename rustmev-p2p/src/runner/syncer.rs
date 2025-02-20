use crate::{
    common::{
        chain::Chain,
        json_rpc::{call_json_rpc, WsJsonRpcData, WsJsonRpcRequest},
    },
    db::models::record::Record,
    util::{json_deep_key, ts_now},
};
use eyre::Ok;
use futures::{future::join_all, stream::SplitSink, SinkExt, StreamExt};
use mongodb::bson::{doc, Bson, DateTime};
use serde_json::{json, Map, Value};
use std::{
    time::{Duration, SystemTime},
    vec,
};
use tokio::{net::TcpStream, task::JoinHandle, time::sleep};
use tokio_tungstenite::{connect_async, tungstenite::Message, MaybeTlsStream, WebSocketStream};

pub struct Syncer {
    chain: Chain,
    last_sync: u64,
    last_fetch: u64,
}

const SYNC_PEERS_PERIOD: u64 = 5 * 60;
const FETCH_PEERS_PERIOD: u64 = 30 * 60;
const SYNC_CONCURRENCY: u16 = 5;

impl Syncer {
    pub fn start(chain: Chain) -> JoinHandle<()> {
        return tokio::spawn(Self::run(chain));
    }

    async fn run(chain: Chain) {
        let mut runner = Syncer {
            chain,
            last_sync: 0,
            last_fetch: 0,
        };
        tokio::spawn(Self::_run_ws(runner.chain.clone()));
        loop {
            let now = ts_now().as_secs();
            if runner.chain.enable_fetch && (now - &runner.last_fetch >= FETCH_PEERS_PERIOD) {
                runner._fetch_peers_from_nodes().await;
                runner.last_fetch = now;
            }
            if runner.chain.enable_sync && (now - &runner.last_sync >= SYNC_PEERS_PERIOD) {
                runner._sync_peers_to_nodes().await;
                runner.last_sync = now;
            }
            sleep(Duration::from_secs(5)).await;
        }
    }

    async fn _run_ws(chain: Chain) {
        if !chain.enable_sync {
            log::warn!("Chain {} is disabled sync.", &chain.chain_name);
            return;
        }
        let result = connect_async(&chain.ws_node).await;
        if let Err(err) = result {
            log::error!("WS connect {} ERROR: {}", &chain.ws_node, err);
            return;
        }
        log::debug!("WS connected -> {}", &chain.ws_node);
        let (ws_stream, _) = result.unwrap();
        let (mut writer, read) = ws_stream.split();

        let subscribe_msg = WsJsonRpcRequest::new(1, "admin_subscribe", vec!["peerEvents"]);
        let sub_result = writer.send(Message::Text(subscribe_msg.encode())).await;
        if let Err(err) = sub_result {
            log::error!("WS subcribe ERROR: {}", err);
        }
        read.for_each(|msg| Self::_on_ws_msg(&chain, &writer, msg)).await;
    }

    async fn _on_ws_msg(
        chain: &Chain,
        _writer: &SplitSink<WebSocketStream<MaybeTlsStream<TcpStream>>, Message>,
        message: Result<Message, tokio_tungstenite::tungstenite::Error>,
    ) {
        let data = WsJsonRpcData::from_ws_msg(message.unwrap()).unwrap();
        if let Some(id) = data.id {
            if id == 1 {
                log::debug!("WS subscribe -> {}", chain.ws_node);
            }
        }

        let params = data.params;
        if params.is_none() {
            return;
        }

        let params = params.unwrap();
        let dtype = json_deep_key(params.clone(), "result.type");
        if dtype.is_none() {
            return;
        }

        match dtype.unwrap().as_str().unwrap() {
            "drop" => {
                let node_id = json_deep_key(params.clone(), "result.peer").unwrap();
                if let Some(record) = Record::delete_by_node_id(node_id.as_str().unwrap().to_string()).await {
                    log::info!("WS: Record REMOVED -> {}", record);
                }
            }
            _ => (),
        }
    }

    async fn _sync_peers_to_nodes(&self) {
        let sync_time = SystemTime::now().checked_sub(Duration::from_secs(SYNC_PEERS_PERIOD)).unwrap();
        let filter = doc! {
            "chain_id": self.chain.chain_id,
            "last_ping": {"$ne": Bson::Null},
            "chain_name": {"$ne": ""},
            "$or": [
                {"last_sync": Bson::Null},
                {"last_sync": {"$lte": DateTime::from_system_time(sync_time)}}
            ]
        };
        let records = Record::find_all(filter).await.unwrap_or(vec![]);
        if records.is_empty() {
            log::error!("No records to sync!");
            return;
        }

        log::debug!("Start syncing {} records of chain {}...", records.len(), &self.chain.chain_id);

        let mut tasks: Vec<tokio::task::JoinHandle<()>> = vec![];
        for record in records {
            tasks.push(tokio::spawn(self.chain.clone().call_add_peer(record)));
            if tasks.len() as u16 > SYNC_CONCURRENCY {
                join_all(tasks).await;
                tasks = vec![];
            }
        }
        log::debug!("All peers of {} are synced!", self.chain.chain_name);
    }

    async fn _fetch_peers_from_nodes(&self) {
        fn get_js_string(json: &serde_json::Map<String, Value>, key: &str) -> String {
            json.get(key).unwrap().as_str().unwrap().to_string()
        }

        async fn save_peer(info: &Map<String, Value>) -> eyre::Result<Option<Record>> {
            if let Some(ib) = info.get("inbound") {
                let ib = ib.as_bool();
                if ib.is_some() && ib.unwrap() {
                    return Ok(None);
                }
            }

            let enode = get_js_string(info, "enode");
            let record = Record::from_enode(enode)?;
            if let Some(_) = Record::find_by_id(record.id.clone().unwrap()).await {
                return Ok(None);
            }

            Record::create(&record).await?;
            Ok(Some(record))
        }

        for rpc in self.chain.rpc_nodes.iter() {
            log::debug!("Fetching peers from node {}", rpc);
            let resp = call_json_rpc(rpc.to_string(), "admin_peers", json!([])).await;
            if let Err(err) = resp {
                log::error!("Fetch peers from {} error -> {}!", rpc, err);
                continue;
            }
            if let Value::Array(peers) = resp.unwrap() {
                for p in peers {
                    let info = p.as_object().unwrap();
                    let res = save_peer(info).await;
                    if res.is_err() {
                        log::error!("Save peer error {:?}", res);
                        continue;
                    }
                    if let Some(record) = res.unwrap() {
                        log::debug!("Fetched from {rpc} -> {}", record);
                    }
                }
            }
        }
    }
}
