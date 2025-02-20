# Python Runner
This project extract MEV exchange cycles from the transactions

## Project Structure

```
python/
├── abi/              # Contract ABI definitions
├── scripts/          # Utility scripts
├── src/              # Main source code
│   ├── runners/      # Runner implementations
│   ├── utils/        # Utility functions
│   ├── __init__.py   # Runner manager
│   └── mongo.py      # MongoDB connection handler
├── tests/            # Test files
├── main.py           # Entry point
├── requirements.txt  # Python dependencies
└── Dockerfile        # Container configuration
```

## Features

- Multiprocessing support for parallel data extraction
- MongoDB integration for data storage
- Configurable cycle extraction
- Process management with graceful start/stop
- Real-time logging and monitoring

## Configuration

The crawler requires the following environment variables:
```
ETH_HTTP_ENDPOINT=http://your-eth-node:8545
MONGO_URI=mongodb://mongodb:27018/mev?authSource=admin
```

These can be configured in the `docker-compose.yaml` file at the root level.

## Development Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

1. Run the workers:
```bash
python main.py
```

## Docker Setup

The crawler is designed to run in a Docker container. The Dockerfile handles all necessary setup.

Build and run using Docker Compose from the parent directory:
```bash
docker compose up -d py_crawlers
```

## Process Control

The crawler uses MongoDB to control its processes. Update the following MongoDB document:

```js
// cycles_extract_limit (number) - bulk processing limit for cycles extractor
// cycles_extractor_enable (boolean) - enable/disable cycles extractor

// Example:
db.info.updateOne(
  { _id: "cycles_extract_limit" },
  { $set: { value: 500 } }
)
db.info.updateOne(
  { _id: "cycles_extractor_enable" },
  { $set: { value: true } }
)
```

By default, the cycles extractor will get the transactions from the `transactions` collection has `needExtractCycles` field set to `true`, then set to `false` after it finished or failed (with error message in `cyclesError` field).

To set the transaction that need to extract cycles, update the following MongoDB document:

```js
// needExtractCycles (boolean) - transaction that need to extract cycles

// Example:
db.transactions.updateMany(
  { _id: "tx_hash" }, // Or other conditions
  { $set: { needExtractCycles: true } }
)
```
