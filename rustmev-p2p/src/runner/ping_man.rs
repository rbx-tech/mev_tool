use crate::{common::devp2p::DevP2P, config::Config, db::models::record::Record};
use eyre::eyre;
use futures::future::join_all;
use mongodb::bson::{doc, Bson, DateTime};
use std::time::{Duration, SystemTime};
use tokio::{task::JoinHandle, time::sleep};
use tokio_util::time::FutureExt;

pub struct PingMan {}

const PING_PERIOD: u64 = 30 * 60;
const PING_TIMEOUT: u64 = 5000;
const PING_CONCURRENCY: u16 = 20;
const ERR_REMOVE_REACH: u64 = 10;

impl PingMan {
    pub fn start() -> tokio::task::JoinHandle<()> {
        return tokio::spawn(Self::run());
    }

    async fn run() {
        loop {
            let ping_time = SystemTime::now().checked_sub(Duration::from_secs(PING_PERIOD)).unwrap();
            let filter = doc! {
                "$or": [
                    {"last_ping": Bson::Null},
                    {"last_ping": {"$lte": DateTime::from_system_time(ping_time)}}
                ]
            };
            let records = Record::find(filter, None, Some(200), Some(doc! {"last_ping": 1}))
                .await
                .unwrap();
            let mut tasks: Vec<JoinHandle<()>> = vec![];
            for r in records {
                tasks.push(tokio::spawn(Self::_ping_record(r)));
                if tasks.len() as u16 >= PING_CONCURRENCY {
                    join_all(tasks).await;
                    tasks = vec![];
                }
            }
            sleep(Duration::from_secs(5)).await;
        }
    }

    async fn _ping_record(record: Record) {
        let nr = record.to_nr();
        let ping_res = DevP2P::ping_node(nr).timeout(Duration::from_millis(PING_TIMEOUT)).await;

        if let Err(_err) = ping_res {
            return Self::_on_ping_fail(record, eyre!("Timeout!")).await;
        }

        let ping_res = ping_res.unwrap();
        if let Err(err) = ping_res {
            return Self::_on_ping_fail(record, err).await;
        }

        let (hello_msg, status) = ping_res.unwrap();
        let chain_name = status.chain.named();
        if chain_name.is_none() {
            return Self::_on_ping_fail(record, eyre!("Cannot detect chain!")).await;
        }

        let chain_name = chain_name.unwrap().to_string();
        let mut record = record
            .chain_name(chain_name.clone())
            .chain_id(status.chain.id())
            .client(hello_msg.client_version)
            .caps(hello_msg.capabilities)
            .mark_ping_ok();
        record.save().await.expect("Save record ERROR");

        log::info!("Ping OK -> {}", record);
    }

    async fn _on_ping_fail(record: Record, err: eyre::Report) {
        if record.error_count >= ERR_REMOVE_REACH && record.pong_count == 0 {
            record.delete().await.unwrap();
            let chain = Config::all().chains.iter().find(|c| (c.chain_id as u64) == record.chain_id);
            if let Some(chain) = chain {
                tokio::spawn(chain.call_remove_peer(record.id.clone().unwrap()));
            }
            log::error!("Ping FAIL REMOVED {} -> {}", record, err);
        } else {
            log::warn!("Ping FAIL {} -> {}", record.id.clone().unwrap(), err);
            record.mark_ping_err().save().await.expect("Save record ERROR");
        }
    }
}
