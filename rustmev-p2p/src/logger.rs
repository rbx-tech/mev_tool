pub fn init_logger(level: &str) {
    std::env::set_var("RUST_LOG", format!("rust_mevp2p={level}"));
    env_logger::init();
}
