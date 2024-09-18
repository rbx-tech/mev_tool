import os
import json
import time
import logging
import argparse
import eth_abi
import requests
from typing import Any
from os import path
from hexbytes import HexBytes
from web3 import Web3
from web3.contract import Contract
from utils.helper import read_file, init_logger, chunk_list, write_file_json, read_file_json

RPC_URL = 'http://10.7.0.58:8545'
START = 12100
END = 12200


w3 = Web3(Web3.HTTPProvider(RPC_URL))
UNIVERSAL_ADDR = '0x3fC91A3afd70395Cd496C647d5a6CC9D4B2b7FAD'
UNIROUTERV2_ADDR = '0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'
SUSHI_ROUTER_ADDR = '0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F'
UNI_QUERY_ADDR = '0x5EF1009b9FCD4fec3094a5564047e190D72Bd511'
UNI_FACTORY_ADDR = '0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f'


contracts = {
    UNIVERSAL_ADDR: w3.eth.contract(address=UNIVERSAL_ADDR, abi=read_file('abi/universal.json')),
    UNIROUTERV2_ADDR: w3.eth.contract(address=UNIROUTERV2_ADDR, abi=read_file('abi/uniswap_v2.json')),
    SUSHI_ROUTER_ADDR: w3.eth.contract(address=SUSHI_ROUTER_ADDR, abi=read_file('abi/sushi_router.json')),
    UNI_QUERY_ADDR: w3.eth.contract(address=UNI_QUERY_ADDR, abi=read_file('abi/flashbots_uni_query.json')),
    UNI_FACTORY_ADDR: w3.eth.contract(address=UNI_FACTORY_ADDR, abi=read_file('abi/uni_factory.json')),
}

FILTER_LIST_METHOD = [
    'swapExactTokensForTokens',
    'swapTokensForExactTokens',
    'swapExactETHForTokens',
    'swapTokensForExactETH',
    'swapExactTokensForETH',
    'swapETHForExactTokens'
]

BLACKLIST = read_file_json('config/blacklist.json')
BLACKLIST_METHOD = {
    '0x908fb5ee': "Balancer",
    '0x2170c741': "Balancer",
    "0x0d7d75e0": "Balancer FlashLoan",
    # '0xc2c0245e': "",
    # '0x276856b3': True
}
TOKENS = read_file_json('config/tokens_eth.json')


class Report:
    def __init__(self, output_path: str):
        self.total = 0
        self.count_v3 = 0
        self.count_token_gt_2 = 0
        self.count_router_v2 = 0
        self.count_not_arb = 0
        self.blacklist = 0
        self.count_blacklist_detail = {}
        self.count_ok = 0
        self.output_path = output_path

    @staticmethod
    def init_count():
        return {'remaining_quantity': 0, 'removed_quantity': 0}

    def increase_total(self, count: int = 1):
        self.total += count

    def get_quantity_by_attr(self, attr: str):
        list_filter = ['count_not_arb', 'count_router_v2', 'blacklist', 'count_token_gt_2', 'count_v3']
        remaining_quantity = self.total
        for a in list_filter:
            remaining_quantity -= getattr(self, a)
            if a == attr:
                break

        return {
            'removed_quantity': getattr(self, attr),
            'remaining_quantity': remaining_quantity,
        }

    def increase_arb(self):
        self.count_not_arb += 1

    def increase_v3(self):
        self.count_v3 += 1

    def increase_token_gt_2(self):
        self.count_token_gt_2 += 1

    def increase_router_v2(self):
        self.count_router_v2 += 1

    def increase_blacklist(self, key: str):
        self.blacklist += 1
        self.count_blacklist_detail[key] = self.count_blacklist_detail.get(key, 0) + 1

    def increase_ok(self, count: int = 1):
        self.count_ok += count

    def report(self):
        write_file_json(self.output_path, {
            'total': self.total,
            'count_ok': self.count_ok,
            'not_arb': self.get_quantity_by_attr('count_not_arb'),
            'not_router_v2': self.get_quantity_by_attr('count_router_v2'),
            'blacklist': {
                **self.get_quantity_by_attr('blacklist'),
                'detail': self.count_blacklist_detail
            },
            'token_gt_2': self.get_quantity_by_attr('count_token_gt_2'),
            'is_v3': self.get_quantity_by_attr('count_v3'),
        })


def batch_get_transaction(txs: list[str]) -> list[dict]:
    body = []
    for tx in txs:
        body.append({'jsonrpc': '2.0', 'method': 'eth_getTransactionByHash', 'params': [tx], 'id': tx})
    res = requests.post(RPC_URL, json=body).json()
    return [r['result'] for r in res if r['result'] is not None]


def batch_get_transaction_receipt(txs: list[str]) -> list[dict]:
    body = []
    for tx in txs:
        body.append({'jsonrpc': '2.0', 'method': 'eth_getTransactionReceipt', 'params': [tx], 'id': tx})
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


def process_bundles(bundles: list) -> list[dict]:
    logger.info(f'Process {len(bundles)} bundles')
    reporter.increase_total(len(bundles))

    bundles_map = {}
    filter_txs = []
    victim_tx_hashes = []

    for bundle in bundles:
        if len(bundle['searcher_txs']) == 1:
            if len(bundle['txs']) == 1:
                filter_txs.append({'hash': None, 'searcher_tx': bundle['searcher_txs'][0]})
            else:
                victim_tx_hashes.append(bundle['txs'][0])

            bundles_map[bundle['txs'][0]] = bundle
        else:
            reporter.increase_arb()

    txs = chunk_batch(batch_get_transaction, victim_tx_hashes, 10)
    for tx in txs:
        if tx['to'] is None:
            continue

        result = decode_func_call(Web3.to_checksum_address(tx['to']), tx['input'])
        if result is not None:
            filter_txs.append({**tx, **result})
        else:
            reporter.increase_router_v2()

    transactions = []
    for tx in filter_txs:
        key = tx['hash'] if tx['hash'] is not None else tx['searcher_tx']
        bundle = bundles_map[key]
        transactions.append({
            'blockNum': bundle['block_number'],
            'blockHash': tx.get('blockHash', None),
            'timestamp': bundle['timestamp'],
            'tx_hash': tx.get('hash', None),
            'searcher_tx': bundle['searcher_txs'][0],
            'tx': {
                'hash': tx.get('hash', None),
                'input': tx.get('input', None),
                'transactionIndex': int(tx.get('transactionIndex', '0x0'), 16),
                'from': tx.get('from', None),
                'to': tx.get('to', None),
                'value': tx.get('value', None),
                'funcName': tx.get('funcName', None),
                'funcInputs': tx.get('funcInputs', None)
            },
            'bundle': {
                'hash': f'https://libmev.com/bundles/{bundle['bundle_hash']}',
                'profitEth': bundle['profit_eth'],
                'profitMargin': bundle['profit_margin'],
                'tippedEth': bundle['tipped_eth'],
                'bundleGasUsed': bundle['bundle_gas_used'],
                'gasUsed': bundle['searcher_gas_used'],
                'burnedEth': bundle['burned_eth'],

            }
        })

    return filter_v2(transactions)


def filter_v2(bundles: list) -> list[dict]:
    bundles_searcher_map = {b['searcher_tx']: b for b in bundles}
    txs_receipt = chunk_batch(batch_get_transaction_receipt, list(bundles_searcher_map.keys()), 10)

    def filter_tx_receipt(receipt) -> bool:
        if receipt['status'] != '0x1':
            reporter.increase_arb()
            logger.info(f'tx: {receipt['transactionHash']} - Status fail')
            return False

        v3_data_types = ['int256', 'int256', 'uint160', 'uint128', 'int24']
        count_token = set()
        for l in receipt['logs']:
            address = l['address']
            if address in BLACKLIST:
                reporter.increase_blacklist(BLACKLIST[address])
                logger.info(f'tx: {receipt['transactionHash']} - Blacklist {BLACKLIST[address]}')
                return False

            if l['topics'][0][:10] in BLACKLIST_METHOD:
                reporter.increase_blacklist(BLACKLIST_METHOD[l['topics'][0][:10]])
                logger.info(f'tx: {receipt['transactionHash']} - Blacklist method')
                return False

            if address in TOKENS:
                count_token.add(address)
            if len(count_token) > 2:
                reporter.increase_token_gt_2()
                logger.info(f'tx: {receipt['transactionHash']} - Count token > 2')
                return False
            try:
                eth_abi.decode(v3_data_types, HexBytes(l['data']))
                reporter.increase_v3()
                logger.info(f'tx: {receipt['transactionHash']} - Tx is v3')
                return False
            except Exception:
                pass

        logger.info(f'tx: {receipt['transactionHash']} - OK')
        return True

    txs_receipt_filter = list(filter(filter_tx_receipt, txs_receipt))
    result = []
    for tx in txs_receipt_filter:
        result.append(bundles_searcher_map[tx['transactionHash']])
    return result


def request_libmev(limit: int = 50, offset: int = 0) -> list[dict]:
    now_seconds = int(time.time())
    content = requests.get(
        f'https://api.libmev.com/v1/bundles?timestampRange=1663224162,{now_seconds}&filterByTags=naked_arb,backrun&limit={limit}&offset={offset}&orderByDesc=block_number')
    return json.loads(content.text).get('data', [])


def fetch_data_and_save_to_json():
    results = []
    for i in range(START, END):
        print(f'Process page: {i}')
        bundles = request_libmev(50, i * 50)
        results.extend(bundles)
    write_file_json(f'bundles/bundles_{START}_{END}.json', results)


def run_from_json():
    file_path = f'bundles/bundles_{START}_{END}.json'
    if not os.path.exists(file_path):
        fetch_data_and_save_to_json()

    result = []
    chunks = chunk_list(read_file_json(file_path), 50)
    for chunk in chunks:
        bundles_filter = process_bundles(chunk)
        bundles_filter_len = len(bundles_filter)
        result.extend(bundles_filter)

        reporter.increase_ok(bundles_filter_len)
        logger.info(f'Found {bundles_filter_len} arbitrage on uniswap v2')
        write_file_json(f'bundles/bundles_filter_{START}_{END}.json', result)
        reporter.report()


def run_from_api():
    results = []
    limit = 50
    for i in range(START, END):
        bundles_json = request_libmev(limit, i * limit)
        bundles_filter = process_bundles(bundles_json)
        bundles_filter_len = len(bundles_filter)
        results.extend(bundles_filter)

        reporter.increase_ok(bundles_filter_len)
        logger.info(f'Found {bundles_filter_len} arbitrage on uniswap v2 limit={limit} offset={i * limit} page={i}')
        logger.info(
            '=======================================================================================================')
        write_file_json(f'bundles/bundles_filter_{START}_{END}.json', results)
        reporter.report()


if __name__ == '__main__':
    logger = logging.getLogger()
    path_config = path.join(path.dirname(__file__), 'config/log_config.yml')
    init_logger(path_config)
    reporter = Report(f'bundles/bundles_filter_{START}_{END}_report.json')

    parser = argparse.ArgumentParser(description='A simple CLI tool.')
    parser.add_argument('--mode', type=str, help='Mode crawler libmev', default='api')
    args = parser.parse_args()

    if args.mode == 'json':
        run_from_json()
    else:
        run_from_api()