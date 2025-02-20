use alloy_primitives::FixedBytes;
use enr::{
    k256::ecdsa,
    secp256k1::{Error, PublicKey},
    Enr, EnrPublicKey, NodeId,
};
use eyre::Ok;
use reth_discv4::NodeRecord;
use std::{
    borrow::Borrow,
    net::IpAddr,
    str::FromStr,
    time::{Duration, SystemTime, UNIX_EPOCH},
};

pub fn ts_now() -> Duration {
    let start = SystemTime::now();
    let since_the_epoch = start.duration_since(UNIX_EPOCH).expect("Time went backwards");
    return since_the_epoch;
}

pub fn enr2nr(enr: String) -> NodeRecord {
    let secp256k1: Enr<ecdsa::SigningKey> = enr.parse().unwrap();
    return NodeRecord {
        address: IpAddr::V4(secp256k1.ip4().unwrap()),
        id: FixedBytes::new(secp256k1.public_key().encode_uncompressed()),
        tcp_port: secp256k1.tcp4().unwrap(),
        udp_port: secp256k1.udp4().unwrap(),
    };
}

pub fn enode2nr(enode: String) -> NodeRecord {
    NodeRecord::from_str(&enode).ok().unwrap()
}

/// Builds a `node_id` from a public key.
pub fn pk2nodeid(hex_str: String) -> eyre::Result<String> {
    let bytes = hex::decode(hex_str).map_err(|_| Error::InvalidPublicKey)?;
    let mut full_key = vec![0x04];
    full_key.extend_from_slice(&bytes);

    let pk = PublicKey::from_slice(&full_key)?;
    let node_id = hex::encode(NodeId::from(pk));
    Ok(node_id)
}

pub fn nr2nodeid(nr: NodeRecord) -> eyre::Result<String> {
    let pk = hex::encode(nr.id);
    pk2nodeid(pk)
}

pub fn json_deep_key(value: serde_json::Value, keys: &str) -> Option<serde_json::Value> {
    let mut value = value.borrow();
    let mut keys = keys.split(".");

    while let Some(k) = keys.next() {
        let v = value.get(k);
        if v.is_none() {
            return Some(value.to_owned());
        }
        value = v.unwrap();
    }
    return Some(value.to_owned());
}
