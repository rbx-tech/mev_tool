import json
import time
import logging
import requests
from typing import Any
from web3 import Web3
from os import path
from web3.contract import Contract
from utils.helper import read_file, init_logger, chunk_list, write_file_json

RPC_URL = 'https://eth-pokt.nodies.app'
START = 0
END = 1000


w3 = Web3(Web3.HTTPProvider(RPC_URL))
UNISWAP_ROUTER_V2_ADDRESS = '0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'

contracts = {
    UNISWAP_ROUTER_V2_ADDRESS: w3.eth.contract(address=UNISWAP_ROUTER_V2_ADDRESS, abi=read_file('abi/uniswap_v2.json'))
}

FILTER_LIST_METHOD = [
    "swapExactTokensForTokens",
    "swapTokensForExactTokens",
    "swapExactETHForTokens",
    "swapTokensForExactETH",
    "swapExactTokensForETH",
    "swapETHForExactTokens"
]

BLACKLIST = [
    "0xba12222222228d8ba445958a75a0704d566bf2c8",
    "0x6000da47483062a0d734ba3dc7576ce6a0b645c4",
    "0x111111125421ca6dc452d289314280a0f8842a65"
]

TOKENS = json.loads(read_file("./output/tokens_eth.json"))


def batch_get_transaction(txs: list[str]) -> list[dict]:
    body = []
    for tx in txs:
        body.append({"jsonrpc": "2.0", "method": "eth_getTransactionByHash", "params": [tx], "id": tx})
    res = requests.post(RPC_URL, json=body).json()
    return [r['result'] for r in res]


def batch_get_transaction_receipt(txs: list[str]) -> list[dict]:
    body = []
    for tx in txs:
        body.append({"jsonrpc": "2.0", "method": "eth_getTransactionReceipt", "params": [tx], "id": tx})
    res = requests.post(RPC_URL, json=body).json()
    return [r['result'] for r in res]


def chunk_batch(method, txs: list[str], chunk_size: int) -> list[dict]:
    txs_chunk = chunk_list(txs, chunk_size)
    result = []
    for txs in txs_chunk:
        result.extend(method(txs))
    return result


def decode_func_call(addr: str, data: str) -> None | dict[str, Any]:
    contract: Contract | None = contracts.get(addr)
    if contract is None:
        return None

    (func, args) = contract.decode_function_input(data)
    if func.fn_name in FILTER_LIST_METHOD:
        # uniswap router v2
        return {'funcName': func.fn_name, 'funcInputs': args}


def process_bundles(bundles: list):
    logger.info(f"Process {len(bundles)} bundles")
    transactions = []

    def filter_bundle_arb(bundle: dict) -> bool:
        if len(bundle['searcher_txs']) == 1 and len(bundle['txs']) == 2:
            return True

    bundles = list(filter(filter_bundle_arb, bundles))
    bundles_map = {b['txs'][0]: b for b in bundles}

    txs = chunk_batch(batch_get_transaction, list(bundles_map.keys()), 10)

    txs_swap = []
    for tx in txs:
        result = decode_func_call(Web3.to_checksum_address(tx['to']), tx['input'])
        if result is not None:
            txs_swap.append({**tx, **result})

    for tx in txs_swap:
        bundle = bundles_map[tx['hash']]
        transactions.append({
            'blockNum': bundle['block_number'],
            'blockHash': tx.get('blockHash'),
            'timestamp': bundle['timestamp'],
            'tx_hash': tx['hash'],
            'searcher_tx': bundle['searcher_txs'][0],
            'tx': {
                'hash': tx['hash'],
                'input': tx['input'],
                'transactionIndex': int(tx['transactionIndex'], 16),
                'from': tx['from'],
                'to': tx['to'],
                'value': tx['value'],
                'funcName': tx['funcName'],
                'funcInputs': tx['funcInputs']
            },
            'bundle': {
                'hash': f'https://libmev.com/bundles/{bundle["bundle_hash"]}',
                'profitEth': bundle['profit_eth'],
                'profitMargin': bundle['profit_margin'],
                'tippedEth': bundle['tipped_eth'],
                'bundleGasUsed': bundle['bundle_gas_used'],
                'gasUsed': bundle['searcher_gas_used'],
                'burnedEth': bundle['burned_eth'],

            }
        })

    return transactions


if __name__ == '__main__':
    logger = logging.getLogger()
    path_config = path.join(path.dirname(__file__), "log_config.yml")
    init_logger(path_config)

    results = []
    limit = 50
    for i in range(START, END):
        now_seconds = int(time.time())
        content = requests.get(
            f'https://api.libmev.com/v1/bundles?timestampRange=1663224162,{now_seconds}&filterByTags=naked_arb,backrun&limit={limit}&offset={limit * i}&orderByDesc=block_number')
        bundles_json = json.loads(content.text).get('data', [])
        bundles = process_bundles(bundles_json)
        results.extend(bundles)
        logger.info(f"Found {len(bundles)} on uniswap router v2 limit={limit} offset={i * limit} page={i}")
        logger.info("=======================================================================================================")
        write_file_json(f"output/tx_{START}_{END}.json", results)
