use crate::{
    register_model,
    util::{enode2nr, nr2nodeid},
};
use ::eyre::Result;
use eyre::Ok;
use mongodb::bson::DateTime;
use reth_discv4::NodeRecord;
use reth_eth_wire::Capability;
use serde::{Deserialize, Serialize};
use std::str::FromStr;

#[derive(Debug, Serialize, Deserialize)]
pub struct Record {
    #[serde(rename = "_id", skip_serializing_if = "Option::is_none")]
    pub id: Option<String>,

    pub enode: String,
    pub score: u64,
    pub caps: Vec<String>,
    pub client: String,
    pub chain_id: u64,
    pub chain_name: String,
    pub error_count: u64,
    pub pong_count: u64,
    pub first_resp: Option<DateTime>,
    pub last_resp: Option<DateTime>,
    pub last_ping: Option<DateTime>,
    pub last_sync: Option<DateTime>,
}

impl Clone for Record {
    fn clone(&self) -> Self {
        Self {
            id: self.id.clone(),
            enode: self.enode.clone(),
            score: self.score.clone(),
            caps: self.caps.clone(),
            client: self.client.clone(),
            chain_id: self.chain_id.clone(),
            chain_name: self.chain_name.clone(),
            error_count: self.error_count.clone(),
            pong_count: self.pong_count.clone(),
            first_resp: self.first_resp.clone(),
            last_resp: self.last_resp.clone(),
            last_ping: self.last_ping.clone(),
            last_sync: self.last_ping.clone(),
        }
    }
}

#[allow(unreachable_code)]
impl Record {
    pub fn from_nr(node_record: NodeRecord) -> Self {
        let node_id = nr2nodeid(node_record).unwrap();
        return Self {
            id: Some(node_id),
            enode: format!("{}", node_record),
            score: 1, // TODO: calc score
            caps: vec![],
            client: "".to_string(),
            chain_id: 0,
            chain_name: "".to_string(),
            error_count: 0,
            pong_count: 0,
            first_resp: None,
            last_resp: None,
            last_ping: None,
            last_sync: None,
        };
    }

    pub async fn delete_by_node_id(node_id: String) -> Option<Self> {
        let record = Record::find_by_id(node_id).await;
        if record.is_none() {
            return None;
        }
        let record = record.unwrap();
        record.delete().await.ok();
        Some(record)
    }

    pub fn from_enode(enode: String) -> Result<Self> {
        Ok(Self::from_nr(NodeRecord::from_str(&enode)?))
    }

    pub fn chain_id(mut self, chain_id: u64) -> Self {
        self.chain_id = chain_id;
        return self;
    }
    pub fn client(mut self, client: String) -> Self {
        self.client = client;
        return self;
    }

    pub fn chain_name(mut self, chain_name: String) -> Self {
        self.chain_name = chain_name;
        return self;
    }

    pub fn caps(mut self, caps: Vec<Capability>) -> Self {
        self.caps = caps.into_iter().map(|c| format!("{}/{}", c.name, c.version)).collect();
        return self;
    }

    pub fn mark_ping_ok(mut self) -> Self {
        if self.first_resp.is_none() {
            self.first_resp = Some(DateTime::now());
        }
        self.last_resp = Some(DateTime::now());
        self.last_ping = Some(DateTime::now());
        self.pong_count += 1;
        self.error_count = 0;
        return self;
    }

    pub fn mark_ping_err(mut self) -> Self {
        self.last_ping = Some(DateTime::now());
        self.error_count += 1;
        return self;
    }

    pub fn to_nr(&self) -> NodeRecord {
        enode2nr(self.enode.clone())
    }
}

impl std::fmt::Display for Record {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        let cname = self.chain_name.clone();
        if self.chain_name.clone() != "" {
            write!(f, "{} ({}/{})", self.id.clone().unwrap(), cname, self.chain_id.clone())
        } else {
            write!(f, "{}", self.id.clone().unwrap())
        }
    }
}

register_model!("records", Record);
