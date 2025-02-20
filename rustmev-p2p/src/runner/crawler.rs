use crate::{
    common::devp2p::DevP2P,
    constants::DEFAULT_BOOTNODES,
    db::models::record::Record,
    util::{enode2nr, enr2nr, pk2nodeid, ts_now},
};
use alloy_primitives::FixedBytes;
use futures::future::{BoxFuture, FutureExt};
use mongodb::bson::doc;
use reth_discv4::{DiscoveryUpdate, NodeRecord};
use std::time::Duration;
use tokio::time::sleep;
use tokio_stream::StreamExt;

pub struct Crawler {}

const DISCV_BREAK_SEC: u64 = 30 * 60;

impl Crawler {
    pub fn start() -> tokio::task::JoinHandle<()> {
        return tokio::spawn(async {
            loop {
                Self::_discv4().await;
                sleep(Duration::from_secs(5)).await;
            }
        });
    }

    async fn _discv4() {
        let filter = doc! {"pong_count": {"$gt": 0}};
        let mut bootnodes: Vec<NodeRecord> = if let Some(nodes) = Record::distinct_all("enode".to_string(), filter).await {
            nodes.into_iter().map(|n| enode2nr(n.as_str().unwrap().to_string())).collect()
        } else {
            vec![]
        };

        if bootnodes.len() == 0 {
            bootnodes = DEFAULT_BOOTNODES.iter().map(|s| enr2nr(s.to_string())).collect()
        }

        log::debug!("Start discovering from {} boot nodes...", bootnodes.len());
        let mut updates = DevP2P::discv4(bootnodes).await;
        let start_time = ts_now().as_secs();
        while let Some(update) = updates.next().await {
            Self::_on_updates(update).await;
            if ts_now().as_secs() - start_time >= DISCV_BREAK_SEC {
                break;
            }
        }
        log::error!("Crawler was stopped!");
    }

    fn _on_updates(update: DiscoveryUpdate) -> BoxFuture<'static, ()> {
        async {
            match update {
                DiscoveryUpdate::EnrForkId(nr, _fork_id) => Self::_handle_added(nr).await,
                DiscoveryUpdate::Added(nr) => Self::_handle_added(nr).await,
                // DiscoveryUpdate::Removed(id) => Self::_handle_deleted(id).await,
                DiscoveryUpdate::DiscoveredAtCapacity(nr) => Self::_handle_added(nr).await,
                DiscoveryUpdate::Batch(batch_updates) => {
                    while let Some(ud) = batch_updates.iter().next() {
                        Self::_on_updates(ud.to_owned()).await;
                    }
                }
                _ => {}
            }
        }
        .boxed()
    }

    async fn _handle_added(nr: NodeRecord) {
        let mut record = Record::from_nr(nr);
        if let Some(_) = Record::find_by_id(record.id.clone().unwrap()).await {
            return;
        }

        if let Err(err) = record.save().await {
            log::error!("Add record ERROR: {:?}", err);
            return;
        }

        log::debug!("Record ADDED -> {}", record);
    }

    async fn _handle_deleted(id: FixedBytes<64>) {
        let node_id = pk2nodeid(hex::encode(id)).unwrap();
        let record = Record::delete_by_node_id(node_id).await;
        if record.is_none() {
            return;
        }
        log::warn!("Record REMOVED -> {}", record.unwrap());
    }
}
