use crate::{common::json_rpc::call_json_rpc, db::models::record::Record};
use futures::future::join_all;
use mongodb::bson::{doc, DateTime};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use tokio::task::JoinHandle;

#[derive(Debug, Serialize, Deserialize)]
pub struct Chain {
    pub chain_id: i64,
    pub chain_name: String,
    pub rpc_nodes: Vec<String>,
    pub ws_node: String,
    pub enable_sync: bool,
    pub enable_fetch: bool,
}
impl Clone for Chain {
    fn clone(&self) -> Self {
        Self {
            chain_id: self.chain_id.clone(),
            chain_name: self.chain_name.clone(),
            rpc_nodes: self.rpc_nodes.clone(),
            ws_node: self.ws_node.clone(),
            enable_sync: self.enable_sync.clone(),
            enable_fetch: self.enable_fetch.clone(),
        }
    }
}

impl Chain {
    pub async fn call_remove_peer(&self, node_id: String) {
        if !self.enable_sync {
            return;
        }
        let mut tasks: Vec<JoinHandle<eyre::Result<Value>>> = vec![];
        for rpc in self.rpc_nodes.clone() {
            let task = tokio::spawn(call_json_rpc(rpc, "admin_removePeer", json!([&node_id])));
            tasks.push(task);
        }
        for rpc in self.rpc_nodes.clone() {
            if let Err(err) = call_json_rpc(rpc, "admin_removePeer", json!([&node_id])).await {
                log::error!("Remove peer ERROR: {}", err);
            }
        }
    }

    pub async fn call_add_peer(self, record: Record) {
        if !self.enable_sync {
            return;
        }
        let mut tasks: Vec<JoinHandle<eyre::Result<Value>>> = vec![];
        for rpc in self.rpc_nodes.clone() {
            let task = tokio::spawn(call_json_rpc(rpc, "admin_addPeer", json!([&record.enode])));
            tasks.push(task);
        }
        for result in join_all(tasks).await.iter() {
            if let Err(err) = result {
                log::error!("Sync peer ERROR: {}", err);
            }
        }
        Record::set_fields_by_id(record.id.unwrap(), doc! {"last_sync": DateTime::now()})
            .await
            .unwrap();
    }
}
