use crate::common::chain::Chain;
use once_cell::sync::OnceCell;
use serde::Deserialize;
use std::fs;

#[allow(dead_code)]
pub static CONFIG_INSTANCE: OnceCell<Config> = OnceCell::new();

#[derive(Debug, Deserialize)]
pub struct Config {
    pub mongo_uri: String,
    pub log_level: String,
    pub chains: Vec<Chain>,
}

impl Config {
    pub fn all() -> &'static Self {
        CONFIG_INSTANCE.get().unwrap()
    }

    pub fn parse() -> &'static Self {
        let content = fs::read_to_string("./config.toml").expect("Read config error:");
        let config = toml::from_str::<Config>(&content).expect("Parse config error:");
        CONFIG_INSTANCE.set(config).unwrap();
        Self::all()
    }
}
