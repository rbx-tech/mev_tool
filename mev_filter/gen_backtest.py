import os
import re
import copy
import argparse
import requests
from utils.helper import read__file_json, write_file_json

URL_RPC = 'http://10.7.0.58:8545'


def decode_rs(num: int):
    bit_length = num.bit_length() + 1
    uint32_bits = 32
    u112_bits = 112

    ts = num >> (bit_length - uint32_bits)
    shift_for_second_part = bit_length - uint32_bits - u112_bits
    rs1 = (num >> shift_for_second_part) & ((1 << u112_bits) - 1)
    rs0 = num & ((1 << u112_bits) - 1)

    return ts, rs0, rs1


def is_hex(value):
    if isinstance(value, str):
        return re.fullmatch(r'0x[0-9a-fA-F]+', value) is not None
    return False


def get_bundle_detail(bundle_hash: str):
    url = bundle_hash.replace('libmev.com/bundles', 'api.libmev.com/v1/bundles')
    return requests.get(url).json()


def get_bundle_profits_raw(profits_raw: dict):
    profit_raw = []
    for p in profits_raw.keys():
        if is_hex(p):
            profit_raw.append(p)
            profit_raw.append(profits_raw[p])
    return profit_raw


def get_rs(block_hash: str, tx_idx: int, pair_address: str):
    body = {
        'method': 'debug_storageRangeAt',
        'params': [
            block_hash,
            tx_idx,
            pair_address,
            '0x0000000000000000000000000000000000000000000000000000000000000000',
            6
        ],
        'id': 1,
        'jsonrpc': 2.0
    }

    res = requests.post(URL_RPC, json=body).json()
    storage = res['result']['storage']
    if storage is None:
        return None

    for item in storage:
        if storage[item]['key'] == '0x0000000000000000000000000000000000000000000000000000000000000008':
            return decode_rs(int(storage[item]['value'], 16))


class Factory:
    def __init__(self):
        self.pairs = {}
        self.dexs = {}

    def get_key(self, pair):
        token0 = pair['token0']
        token1 = pair['token1']
        return '_'.join(sorted([token0, token1]))

    def get_pairs(self, token0, token1):
        key = self.get_key({'token0': token0, 'token1': token1})
        pairs = self.pairs.get(key)
        if pairs is None:
            return []

        dexs = []
        for pair in self.pairs.get(key):
            dexs.append({
                **self.dexs[pair['dex']],
                'pairs': [pair]
            })

        return dexs

    def load(self, folder_path: str):
        for file_name in os.listdir(folder_path):
            file_path = os.path.join(folder_path, file_name)
            file_name = os.path.splitext(file_name)[0]
            pairs = read__file_json(file_path)

            self.dexs[file_name] = {
                'router_address': pairs['router_address'],
                'factory_address': pairs['factory_address'],
            }

            for pair in pairs['pairs']:
                pair = {
                    'address': pair['address'],
                    'token0': pair['token0']['address'],
                    'token1': pair['token1']['address'],
                    'dex': file_name,
                    'reserves': []
                }
                if self.pairs.get(self.get_key(pair)) is None:
                    self.pairs[self.get_key(pair)] = [pair]
                else:
                    self.pairs[self.get_key(pair)].append(pair)


factory = Factory()
factory.load('./pairs')


def format_tx(tx):
    token0 = tx['tx']['funcInputs']['path'][0].lower()
    token1 = tx['tx']['funcInputs']['path'][1].lower()

    dexs = copy.deepcopy(factory.get_pairs(token0, token1))
    if dexs is not None and len(dexs) > 1:
        for dex in dexs:
            rs = get_rs(tx['blockHash'], tx['tx']['transactionIndex'], dex['pairs'][0]['address'])
            if rs is not None:
                dex['pairs'][0]['reserves'].append(str(rs[1]))
                dex['pairs'][0]['reserves'].append(str(rs[2]))
                del dex['pairs'][0]['dex']
    else:
        return None

    bundle_detail = get_bundle_detail(tx['bundle']['hash'])

    return {
        'tx_hash': tx['tx_hash'],
        'bundle': tx['bundle']['hash'],
        'block_num': tx['blockNum'],
        'mev': {
            'profit_eth': tx['bundle']['profitEth'],
            'profit_margin': tx['bundle']['profitMargin'],
            'tipped_eth': tx['bundle']['tippedEth'],
            'bundle_gas_used': tx['bundle']['bundleGasUsed'],
            'gas_used': tx['bundle']['gasUsed'],
            'burned_eth': tx['bundle']['burnedEth'],
        },
        'profits_raw': get_bundle_profits_raw(bundle_detail['profits_raw']),
        'dexs': dexs
    }


def main():
    parser = argparse.ArgumentParser(description='Generate backtest')
    parser.add_argument('--p', type=str, required=True, help='Path file bundle json')
    parser.add_argument('--o', type=str, default='./backtest/backtest.json', help='Path file output json')
    args = parser.parse_args()

    backtests = []
    txs = read__file_json(args.p)
    for tx in txs:
        tx = format_tx(tx)
        if tx is not None:
            backtests.append(tx)

    write_file_json(args.o, backtests)


if __name__ == '__main__':
    main()
