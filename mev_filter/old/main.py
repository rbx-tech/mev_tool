import json
import time
import os
from time import sleep
from typing import Any
import eth_abi.decoding
import requests
from web3 import Web3
import web3
import web3.contract
import eth_abi
import web3.eth
import web3.types

w3 = Web3(Web3.HTTPProvider('https://rpc.ankr.com/eth'))


def read_file(file: str):
    with open(file) as f:
        return f.read()


UNIVERSAL_ADDR = '0x3fC91A3afd70395Cd496C647d5a6CC9D4B2b7FAD'
UNIROUTERV2_ADDR = '0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'
SUSHI_ROUTER_ADDR = '0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F'
UNI_QUERY_ADDR = '0x5EF1009b9FCD4fec3094a5564047e190D72Bd511'
UNI_FACTORY_ADDR = '0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f'


contracts = {
    UNIVERSAL_ADDR: w3.eth.contract(address=UNIVERSAL_ADDR, abi=read_file('../abi/universal.json')),
    UNIROUTERV2_ADDR: w3.eth.contract(address=UNIROUTERV2_ADDR, abi=read_file('../abi/uniswap_v2.json')),
    SUSHI_ROUTER_ADDR: w3.eth.contract(address=SUSHI_ROUTER_ADDR, abi=read_file('../abi/sushi_router.json')),
    UNI_QUERY_ADDR: w3.eth.contract(address=UNI_QUERY_ADDR, abi=read_file('../abi/flashbots_uni_query.json')),
    UNI_FACTORY_ADDR: w3.eth.contract(address=UNI_FACTORY_ADDR, abi=read_file('../abi/uni_factory.json')),
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

TOKENS = json.loads(read_file("../output/tokens_eth.json"))


def process_bundles(bundles: list):
    print("bundles ", len(bundles))
    transactions = []
    for b in bundles:
        txs = b['txs']
        tx_hash = txs[0]
        try:
            tx = w3.eth.get_transaction(tx_hash)
        except Exception as e:
            print(f'error get tx {tx_hash} ', e)
            continue

        if len(b['searcher_txs']) > 1 or len(b['txs']) > 2:
            # print(f'Tx {tx_hash} is not arbitrage. Abort!')
            continue

        contract_addr = str(tx['to'])

        if contract_addr == UNIROUTERV2_ADDR:
            print("tx ", tx['input'].to_0x_hex())

        result = decode_func_call(contract_addr, tx['input'].to_0x_hex())
        if result is None:
            continue

        transactions.append({
            'blockNum': b['block_number'],
            'blockHash': tx.get('blockHash').to_0x_hex(),
            'timestamp': b['timestamp'],
            'tx_hash': tx_hash,
            'searcher_txs': b['searcher_txs'][0],
            'tx': {
                "accessList": tx.get('accessList'),
                "data": tx.get('data').hex() if tx.get('data') else None,
                "from": str(tx['from']),
                "gas": tx['gas'],
                "gasPrice": tx['gasPrice'],
                "maxFeePerBlobGas": tx.get('maxFeePerBlobGas'),
                "maxFeePerGas": tx.get('maxFeePerGas'),
                "maxPriorityFeePerGas": tx.get('maxPriorityFeePerGas'),
                "hash": tx_hash,
                "nonce": int(tx['nonce']),
                "r": tx['r'].to_0x_hex(),
                "s": tx['s'].to_0x_hex(),
                "to": contract_addr,
                "transactionIndex": tx['transactionIndex'],
                "type": tx['type'],
                "v": tx['v'],
                "value": tx['value'],
                "yParity": tx.get('yParity'),
                **result,
            },
            'bundle': {
                "hash": f'https://libmev.com/bundles/{b['bundle_hash']}',
                'profitEth': b['profit_eth'],
                'profitMargin': b['profit_margin'],
                'tippedEth': b['tipped_eth'],
                'bundleGasUsed': b['bundle_gas_used'],
                'gasUsed': b['searcher_gas_used'],
                'burnedEth': b['burned_eth'],
            }
        })

    return transactions


def decode_func_call(addr: str, data: str) -> None | dict[str, Any]:
    contract: web3.contract.Contract | None = contracts.get(addr)
    if contract is None:
        return None

    (func, args) = contract.decode_function_input(data)
    if func.fn_name in FILTER_LIST_METHOD:
        # uniswap router v2
        return {'funcName': func.fn_name, 'funcInputs': args}


def filter_v2(w3: web3.Web3, tx_hash: str):
    count_token = set()
    try:
        receipt = w3.eth.get_transaction_receipt(tx_hash)
    except Exception:
        return False, 'get_transaction_receipt error'

    v3_data_types = ['int256', 'int256', 'uint160', 'uint128', 'int24']
    v2_data_types = ['uint256', 'uint256', 'uint256', 'uint256']

    for l in receipt['logs']:
        addr = l['address'].lower()

        if addr in BLACKLIST:
            return False, 'blacklist'

        if addr in TOKENS:
            count_token.add(addr)

        if len(count_token) > 2:
            return False, 'token > 2'
        
        try:
            eth_abi.decode(v3_data_types, l['data'])
            return False, 'v3'
        except Exception:
            pass

        try:
            eth_abi.decode(v2_data_types, l['data'])
            if all_pairs[addr] is None:
                return False, 'not in all_pairs'
            continue
        except Exception as e:
            continue

    return True, ''


def get_all_pairs():
    file_path = '../output/all_pairs.json'
    if os.path.exists(file_path):
        with open(file_path) as f:
            return json.loads(f.read())

    factory_factory: web3.contract.Contract = contracts[UNI_FACTORY_ADDR]
    pair_length = factory_factory.caller.call_function(factory_factory.get_function_by_name('allPairsLength'))

    all_pairs = {}
    query_factory: web3.contract.Contract = contracts[UNI_QUERY_ADDR]
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
    all_pairs = get_all_pairs()
    results = []
    limit = 50
    for i in range(1850, 2000):
        now_seconds = int(time.time())
        content = requests.get(
            f'https://api.libmev.com/v1/bundles?timestampRange=1663224162,{now_seconds}&filterByTags=naked_arb,backrun&limit={limit}&offset={limit * i}&orderByDesc=block_number')
        bundles = json.loads(content.text).get('data', [])
        txs = []

        start_time = time.time()
        for tx in process_bundles(bundles):
            (is_only_v2, reason) = filter_v2(w3, tx['searcher_txs'])
            print(tx['searcher_txs'], is_only_v2, reason)
            if is_only_v2 and tx['tx']['funcInputs'].get('path'):
                txs.append(tx)
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"Thời gian chạy của hàm: {execution_time} giây")

        results.extend(txs)
        print(f"Found {len(txs)} arbitrage on uniswap v2 limit={limit} offset={i*limit} page={i}")

        with open('../output/tx.json', 'w') as f:
            f.write(json.dumps(results, indent=3))

        sleep(1)