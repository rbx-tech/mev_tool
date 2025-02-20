# Rust MEV P2P

A Rust-based DevP2P network crawler and synchronizer for MEV node. Support multi-chain.
## Features

- DevP2P Network Crawler: Discovers and maintains connections with Ethereum network nodes
- Node Ping Management: Actively monitors node availability and health
- Multi-Chain Support: Configurable for different Ethereum networks

## Prerequisites

- Rust 2021 edition or later
- MongoDB instance
- Docker (optional, for containerized deployment)

## Installation


1. Configure the application:
```bash
cp config.toml.example config.toml
# Edit config.toml with your settings
```

2. Build the project:
```bash
cargo build --release
```

## Configuration

Create a `config.toml` file based on the provided example. Key configuration options include:

- MongoDB connection URI
- Chain configurations
- Logging level
- Network parameters

## Config chain example

```toml
# ....
[[chains]]
ws_node = "ws://192.168.1.58:8546"
chain_name = "Eth"
chain_id = 1
enable_sync = true
enable_fetch = true
rpc_nodes = ["http://192.168.1.58:8545"]

# Other chains config
[[chains]]
ws_node = "ws://10.7.0.58:8746"
chain_name = "Ronin"
chain_id = 2020
enable_sync = true
enable_fetch = true
rpc_nodes = ["http://10.7.0.58:8745"]
# ....
```

## Running the Application

### Direct Execution

```bash
cargo run --release
```

### Using Docker

```bash
# Run using docker-compose
docker compose up -t --build
```

## Project Structure

- `/src`
  - `/common` - Shared utilities and chain-specific implementations
  - `/db` - MongoDB integration and data models
  - `/runner` - Core components (crawler, ping manager, syncer)
  - `config.rs` - Configuration management
  - `constants.rs` - System constants
  - `main.rs` - Application entry point

## How does it work?
1. Crawler module - Use devp2p to crawl the network and maintain connections with nodes.
2. PingMan module - Check node health and availability.
3. Syncer module - Broadcast peers to target nodes.
