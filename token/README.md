# MEV Token Analysis Tool

A Python-based tool for analyzing token fees.

## Features

- Token contract interaction and analysis
- Support for both Uniswap V2 and V3 protocols
- EVM simulation using pyrevm
- Smart path routing for token swaps
- Token fee analysis and verification

## Prerequisites

- Python 3.12
- Virtual environment (recommended)

## Installation

2. Create and activate a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Project Structure

- `abi/` - Contains ABI definitions for various contracts (WETH, ERC20, Uniswap)
- `contract.py` - Base contract interaction class with Custom PyRevM support
- `abi.py` - ABI handling utilities
- `ensure_token_fee.py` - Token fee verification and analysis
- `test.py` - Main testing module
- `tests/` - Test suite for contract interactions and swaps

## Usage

### Token Fee Analysis
```bash
python ensure_token_fee.py --rpc_url http://192.168.1.58:8545 --file_path data/token.txt
```

The output will be saved to `data/` folder.