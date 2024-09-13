import os
import json
import time
import logging
import eth_abi
import requests
from typing import Any
from os import path
from hexbytes import HexBytes
from web3 import Web3
from web3.contract import Contract
from utils.helper import read_file, init_logger, chunk_list, write_file_json

RPC_URL = 'https://rpc.ankr.com/eth'
START = 0
END = 2


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

BLACKLIST = [
    '0xba12222222228d8ba445958a75a0704d566bf2c8',
    '0x6000da47483062a0d734ba3dc7576ce6a0b645c4',
    '0x111111125421ca6dc452d289314280a0f8842a65',
    '0x4fd2d9d6ef05e13bf0b167509151a4ec3d4d4b93',
    '0xa49b3c7c260ce8a7c665e20af8aa6e099a86cf8a',
    '0xa65405e0dd378c65308deae51da9e3bcebb81261',
    '0xb3284f2f22563f27cef2912637b6a00f162317c4',
    '0x6a3b875854f5518e85ef97620c5e7de75bbc3fa0',
    '0x661b94d96adb18646e791a06576f7905a8d1bef6',
    '0x7350c6d00d63ab5988250aea347f277c19bea785',
    '0x02566303a0e860ec66d3b79168459978b1b00c8e',
    '0x408e75c26e6182476940ece5b0ba6491b4f13359',
    '0x655ad905dec61e4fb7d4840a1f450685801511b2',
    '0xaaf841fd6409c136fa4b960e22a92b45b26c9b41'
]

TOKENS = json.loads(read_file('./output/tokens_eth.json'))


class Report:
    def __init__(self, output_path: str):
        self.total = 0
        self.count_v3 = 0
        self.count_token_gt_2 = 0
        self.count_router_v2 = 0
        self.count_arb = 0
        self.blacklist = 0
        self.count_ok = 0
        self.output_path = output_path

    def increase_total(self, count: int = 1):
        self.total += count

    def increase_ok(self, count: int = 1):
        self.count_ok += count

    def increase_v3(self):
        self.count_v3 += 1

    def increase_token_gt_2(self):
        self.count_token_gt_2 += 1

    def increase_router_v2(self):
        self.count_router_v2 += 1

    def increase_arb(self):
        self.count_arb += 1

    def increase_blacklist(self):
        self.blacklist += 1

    def report(self):
        write_file_json(self.output_path, {
            'total': self.total,
            'blacklist': self.blacklist,
            'count_v3': self.count_v3,
            'count_arb': self.count_arb,
            'count_token_gt_2': self.count_token_gt_2,
            'count_router_v2': self.count_router_v2,
            'count_ok': self.count_ok
        })


def batch_get_transaction(txs: list[str]) -> list[dict]:
    body = []
    for tx in txs:
        body.append({'jsonrpc': '2.0', 'method': 'eth_getTransactionByHash', 'params': [tx], 'id': tx})
    res = requests.post(RPC_URL, json=body).json()
    return [r['result'] for r in res]


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
    transactions = []

    def filter_bundle_arb(bundle: dict) -> bool:
        if len(bundle['searcher_txs']) == 1 and len(bundle['txs']) == 2:
            return True
        else:
            reporter.increase_arb()

    bundles = list(filter(filter_bundle_arb, bundles))
    bundles_map = {b['txs'][0]: b for b in bundles}

    txs = chunk_batch(batch_get_transaction, list(bundles_map.keys()), 10)

    txs_swap = []
    for tx in txs:
        result = decode_func_call(Web3.to_checksum_address(tx['to']), tx['input'])
        if result is not None:
            txs_swap.append({**tx, **result})
        else:
            reporter.increase_router_v2()

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
                'hash': f'https://libmev.com/bundles/{bundle['bundle_hash']}',
                'profitEth': bundle['profit_eth'],
                'profitMargin': bundle['profit_margin'],
                'tippedEth': bundle['tipped_eth'],
                'bundleGasUsed': bundle['bundle_gas_used'],
                'gasUsed': bundle['searcher_gas_used'],
                'burnedEth': bundle['burned_eth'],

            }
        })

    return transactions


def filter_v2(bundles: list) -> list[dict]:
    bundles_searcher_map = {b['searcher_tx']: b for b in bundles}
    txs_receipt = chunk_batch(batch_get_transaction_receipt, list(bundles_searcher_map.keys()), 10)

    def filter_tx_receipt(receipt) -> bool:
        v3_data_types = ['int256', 'int256', 'uint160', 'uint128', 'int24']
        v2_data_types = ['uint256', 'uint256', 'uint256', 'uint256']
        count_token = set()
        for l in receipt['logs']:
            address = l['address']
            if address in BLACKLIST:
                reporter.increase_blacklist()
                logger.info(f'tx: {receipt['transactionHash']} - Blacklist')
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

            try:
                eth_abi.decode(v2_data_types, HexBytes(l['data']))
                if all_pairs[address] is None:
                    logger.info(f'tx: {receipt['transactionHash']} - Pair not found')
                    return False
                continue
            except Exception as e:
                continue

        logger.info(f'tx: {receipt['transactionHash']} - OK')
        return True

    txs_receipt_filter = list(filter(filter_tx_receipt, txs_receipt))
    result = []
    for tx in txs_receipt_filter:
        result.append(bundles_searcher_map[tx['transactionHash']])
    return result


def get_all_pairs():
    file_path = 'output/all_pairs.json'
    if os.path.exists(file_path):
        with open(file_path) as f:
            return json.loads(f.read())

    factory_factory: Contract = contracts[UNI_FACTORY_ADDR]
    pair_length = factory_factory.caller.call_function(factory_factory.get_function_by_name('allPairsLength'))

    all_pairs = {}
    query_factory: Contract = contracts[UNI_QUERY_ADDR]
    func = query_factory.get_function_by_name('getPairsByIndexRange')
    index = 0
    while True:
        if index > pair_length:
            break
        pairs = query_factory.caller.call_function(func, UNI_FACTORY_ADDR, index, index + 1000)
        for [x, y, addr] in pairs:
            all_pairs[addr] = [x, y]
        print(f'Added {len(pairs)} pairs')
        index += 1000

    with open(file_path, 'w') as f:
        f.write(json.dumps(all_pairs))


if __name__ == '__main__':
    logger = logging.getLogger()
    path_config = path.join(path.dirname(__file__), 'log_config.yml')
    init_logger(path_config)
    reporter = Report(f'output/tx_{START}_{END}_report.json')

    all_pairs = get_all_pairs()
    results = []
    limit = 50
    for i in range(START, END):
        now_seconds = int(time.time())
        content = requests.get(
            f'https://api.libmev.com/v1/bundles?timestampRange=1663224162,{now_seconds}&filterByTags=naked_arb,backrun&limit={limit}&offset={limit * i}&orderByDesc=block_number')
        bundles_json = json.loads(content.text).get('data', [])

        bundles = process_bundles(bundles_json)
        bundles_filter = filter_v2(bundles)
        bundles_filter_len = len(bundles_filter)
        results.extend(bundles_filter)

        reporter.increase_ok(bundles_filter_len)
        logger.info(f'Found {bundles_filter_len} arbitrage on uniswap v2 limit={limit} offset={i * limit} page={i}')
        logger.info('=======================================================================================================')
        write_file_json(f'output/tx_{START}_{END}.json', results)
        reporter.report()