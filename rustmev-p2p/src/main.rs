// Module define
pub mod db {
    pub mod models {
        pub mod record;
    }
    pub mod mongo;
    pub mod util;
}
pub mod common {
    pub mod chain;
    pub mod devp2p;
    pub mod json_rpc;
}
pub mod runner {
    pub mod crawler;
    pub mod ping_man;
    pub mod syncer;
}
pub mod config;
pub mod constants;
pub mod logger;
pub mod util;

use config::Config;
use db::mongo::MongoDB;
use futures::future::join_all;
use logger::init_logger;
use runner::{crawler::Crawler, ping_man::PingMan, syncer::Syncer};

#[tokio::main]
async fn main() {
    let config = Config::parse();
    init_logger(&config.log_level);
    MongoDB::connect(&config.mongo_uri).await;
    log::debug!("DevP2P is runing!");

    let mut tasks: Vec<tokio::task::JoinHandle<()>> = vec![];

    tasks.push(Crawler::start());
    tasks.push(PingMan::start());

    for chain in config.chains.iter() {
        Syncer::start(chain.clone());
    }

    join_all(tasks).await;
}

#[cfg(test)]
mod tests {
    use crate::util::pk2nodeid;

    #[test]
    fn test_pk2node_id() {
        let hex_str = "cc0c6ac2e850e7b763c8b3b7a63ca020306665460a8c05cbdef224bbe56361782df3bfc26b5c38e48e7358b08c2ffd2102474eb1f21fda6f9fc604f13a27baa6";
        let node_id = pk2nodeid(hex_str.to_string()).unwrap();
        assert_eq!(node_id, "f8eaf76317a6dcf67c04b6227aa480ab0b00600fa12c5458bd3e735814ca84ec");
    }
}
