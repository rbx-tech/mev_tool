# Node.js Crawler

This is the Node.js implementation of the MEV tool crawler. It includes various parsers and runners for data collection and processing.

## Prerequisites

- Node.js (v16 or higher recommended)
- MongoDB
- npm or yarn package manager

## Installation

1. Install dependencies:
```bash
npm install
```

## Project Structure

- `parsers/`: Contains parsing logic for different data sources (Deprecated, just use for migrate data)
- `runners/`: Contains main runner implementations
  - `eigenphy/`: Eigenphy bundle runner for crawling [eigenphy.com](https://eigenphi.io/) bundles
  - `etherscan/`: Etherscan transaction crawler for fetching transaction details (Incompleted yet)
  - `libmev/`: LibMEV bundle runner for crawling [libmev.com](https://libmev.com/) bundles
- `scripts/`: Contains utility scripts (reports, etc.)
- `utils/`: Contains shared utility functions
- `mongo.js`: MongoDB connection and utilities
- `index.js`: Main entry point

## Prerequisites
A list of proxy need to be placed in `resources/proxy_socks5.txt`. See the `utils/proxy4.js` and `utils/proxy6.js` for more details.


## Usage

### Run the workers on development environment:
```bash
node index.js
```

### Run on docker:
- Navigate to the root directory of the project
- Run the following command:
```bash
docker compose up -d
```


## Worker configs

### Etherscan Transaction Crawler (Incompleted yet)
The Etherscan crawler (`runners/etherscan/tx.js`) fetches transaction details from Etherscan.

### Eigenphy Bundle Crawler
The Eigenphy (`runners/eigenphy/bundle.js`) are responsible for crawling transaction bundles from [eigenphi.io](https://eigenphi.io/).

To enable the Eigenphy crawler, set the flag `eigenphy_enable` to `true` on the `info` collection.
```js
db.info.updateOne(
    { _id: "eigenphy_enable" },
    { $set: { value: true } }
)
```

Default the crawler will run every 6 hours. To set the next run time earlier, update `eigenphy_next_run` in the `info` collection:
```js
db.info.updateOne(
    { _id: "eigenphy_next_run" },
    { $set: { value: Date.now() } }
)
```

**Another configs:**
- eigenphy_crawl_limit: limit for each crawl, default is 1000
- eigenphy_cusor: timestamp (int seconds) for the last crawled transaction, the next run will start from this cursor

### LibMEV Bundle Crawler
The LibMEV (`runners/libmev/bundle.js`) are responsible for crawling transaction bundles from [libmev.com](https://libmev.com/).

To enable the LibMEV crawler, set the flag `libmev_enable` to `true` on the `info` collection.
```js
db.info.updateOne(
    { _id: "libmev_enable" },
    { $set: { value: true } }
)
```

Default the crawler also will run every 6 hours. To set the next run time earlier, update `libmev_next_run` in the `info` collection:
```js
db.info.updateOne(
    { _id: "libmev_next_run" },
    { $set: { value: Date.now() } }
)
```

**Another configs:**
- libmev_crawl_limit: limit for each crawl, default is 20
- libmev_runners: maximum concurrent runners, default is 5

The `runners` will be executed in parallel and can be monitor in the `runners` collection:
