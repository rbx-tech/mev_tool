# MEV Crawlers

A distributed crawler system for blockchain data collection, implemented in both Python and Node.js with MongoDB for data storage.

## Project Structure

- `python/` - Python-based crawler implementation
- `node/` - Node.js-based crawler implementation
- `data/` - MongoDB data storage directory
- `output/` - Build outputs and deployment files


## Prerequisites

- Docker and Docker Compose
- Make (for build scripts)
- MongoDB (runs in container)

## Setup and Installation

1. Configure environment variables:
   - Edit the environment at docker-compose.yaml

2. Start the services:
   ```bash
   docker compose up -d
   ```

This will start:
- MongoDB on port 27018
- Python crawler container
- Node.js crawler container

## Deployment

To package the source code for deployment:
```bash
make zip
```

This creates `output/source.zip` containing all necessary source files, excluding:
- Node.js dependencies (`node_modules`)
- Python virtual environment (`venv`)
- Python cache files (`__pycache__`)
- `package-lock.json`

To deploy to a remote server:
```bash
make upload
```

At the server, unzip the archive using `unzip`, then run:
```bash
docker compose up -d
```

## Logs and Monitoring

- Container logs can be viewed using:
  ```bash
  docker compose logs -f [service_name]
  ```
- MongoDB data can be accessed directly at `mongodb://localhost:27018`

## Stopping Services

```bash
docker compose down
```

