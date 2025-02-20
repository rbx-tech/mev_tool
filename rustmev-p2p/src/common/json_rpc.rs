use eyre::eyre;
use reqwest::Client;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use tokio_tungstenite::tungstenite::Message;

#[derive(Serialize)]
struct JsonRpcRequest<'a> {
    jsonrpc: &'a str,
    method: &'a str,
    params: serde_json::Value,
    id: u64,
}

#[derive(Deserialize, Debug)]
pub struct JsonRpcResponse<T> {
    pub jsonrpc: String,
    pub result: Option<T>,
    pub error: Option<JsonRpcError>,
    pub id: u64,
}

#[derive(Deserialize, Debug)]
pub struct JsonRpcError {
    pub code: i64,
    pub message: String,
    pub data: Option<serde_json::Value>,
}

pub async fn call_json_rpc(url: String, method: &str, params: serde_json::Value) -> eyre::Result<serde_json::Value> {
    let client = Client::new();

    let request = JsonRpcRequest {
        jsonrpc: "2.0",
        method,
        params,
        id: 1,
    };

    let response = client
        .post(url)
        .json(&request)
        .send()
        .await?
        .json::<JsonRpcResponse<serde_json::Value>>()
        .await?;

    if let Some(error) = response.error {
        Err(eyre!(error.message))
    } else {
        Ok(response.result.unwrap_or_default())
    }
}

pub struct WsJsonRpcRequest<T> {
    pub method: String,
    pub jsonrpc: String,
    pub id: u64,
    pub params: Vec<T>,
}

impl<T: Serialize> WsJsonRpcRequest<T> {
    pub fn new(id: u64, method: &str, params: Vec<T>) -> Self {
        WsJsonRpcRequest {
            method: method.to_string(),
            jsonrpc: "2.0".to_string(),
            id,
            params,
        }
    }

    pub fn encode(self) -> String {
        json!({
            "method": self.method,
            "jsonrpc": "2.0",
            "id": self.id,
            "params": self.params
        })
        .to_string()
    }
}

#[derive(Deserialize)]
pub struct WsJsonRpcData {
    pub jsonrpc: String,
    pub id: Option<u64>,
    pub params: Option<Value>,
    pub local: Option<String>,
    pub remote: Option<String>,
}

impl WsJsonRpcData {
    pub fn parse(data: String) -> eyre::Result<Self> {
        Ok(serde_json::from_str::<Self>(&data)?)
    }

    pub fn from_ws_msg(msg: Message) -> eyre::Result<Self> {
        let data = String::from_utf8(msg.into_data())?;
        Ok(Self::parse(data)?)
    }
}
