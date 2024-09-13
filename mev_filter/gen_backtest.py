import os
import re
import copy
import argparse
import requests
import hashlib
from utils.helper import read_file_json, write_file_json, delete_keys_from_dict
from utils.rpc import RPC

URL_RPC = 'http://10.7.0.58:8545'
WETH = '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'
rpc = RPC(URL_RPC)


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
            if profits_raw[p] == 0:
                return [WETH, str(profits_raw['ETH'])]
            else:
                profit_raw.append(p)
                profit_raw.append(str(profits_raw[p]))
    return profit_raw


class Factory:
    def __init__(self):
        self.router_map = {}
        self.pair_map = {}
        self.dexs = {}

    @staticmethod
    def get_router_key(router: str, token0 :str, token1: str):
        key_str = router.lower() + '_'.join(sorted([token0.lower(), token1.lower()]))
        key_hash = hashlib.md5(key_str.encode()).hexdigest()
        return key_hash

    def get_router_pair(self, router: str, token0 :str, token1: str):
        key = self.get_router_key(router, token0, token1)
        return copy.deepcopy(self.router_map.get(key))

    def get_pair(self, pair: str):
        return copy.deepcopy(self.pair_map.get(pair.lower()))

    def get_dex_info(self, dex: str):
        return {
            'name': dex,
            **self.dexs.get(dex)
        }

    def load(self, folder_path: str):
        for file_name in os.listdir(folder_path):
            file_path = os.path.join(folder_path, file_name)
            file_name = os.path.splitext(file_name)[0]
            dex = read_file_json(file_path)

            self.dexs[file_name] = {
                'router_address': dex['router_address'],
                'factory_address': dex['factory_address'],
            }

            self.init_map(dex, file_name)

    def init_map(self, dex: dict, file_name: str):
        for pair in dex['pairs']:
            router = dex['router_address']
            token0 = pair['token0']['address']
            token1 = pair['token1']['address']
            pair = {
                'address': pair['address'],
                'token0': token0,
                'token1': token1,
                'dex': file_name,
                'symbols': [pair['token0']['symbol'], pair['token1']['symbol']],
                'reserves': []
            }
            self.router_map[self.get_router_key(router, token0, token1)] = pair
            self.pair_map[pair['address'].lower()] = pair


factory = Factory()
factory.load('./pairs')


def get_pairs_tx_victim(bundle) -> list[dict]:
    pairs = []
    path = bundle['tx']['funcInputs']['path']
    router = bundle['tx']['to']
    for i in range(len(path) - 1):
        token0 = path[i].lower()
        token1 = path[i + 1].lower()
        pair = factory.get_router_pair(router, token0, token1)
        if pair is None:
            raise Exception(f"Pair not found: {router} - {token0} - {token1}")
        rs = rpc.get_rs_at_tx(bundle['blockHash'], bundle['tx']['transactionIndex'], pair['address'])
        if rs is not None:
            pair['reserves'].append(str(rs[1]))
            pair['reserves'].append(str(rs[2]))
            pairs.append(pair)

    return pairs


def get_pairs_tx_mev(bundle) -> list[dict]:
    pairs = []
    logs = rpc.get_tx_receipt(bundle['searcher_tx'])['logs']
    for log in logs:
        addr = log['address']
        pair = factory.get_pair(addr)
        if pair is not None:
            rs = rpc.get_rs_at_tx(bundle['blockHash'], bundle['tx']['transactionIndex'], pair['address'])
            if rs is not None:
                pair['reserves'].append(str(rs[1]))
                pair['reserves'].append(str(rs[2]))
                pairs.append(pair)

    return pairs


def push_to_dexs(dexs, pair):
    idx_dex = -1
    dex_pair = factory.get_dex_info(pair['dex'])
    for i, dex in enumerate(dexs):
        if dex['router_address'] == dex_pair['router_address']:
            idx_dex = i
            break

    if idx_dex == -1:
        dexs.append({
            **dex_pair,
            'pairs': [delete_keys_from_dict(pair, ['dex'])]
        })
    else:
        pairs = dexs[idx_dex]['pairs']
        for p in pairs:
            if p['address'] == pair['address']:
                return
        pairs.append(delete_keys_from_dict(pair, ['dex']))


def format_bundle(bundle):
    dexs = []
    for pair in get_pairs_tx_victim(bundle):
        push_to_dexs(dexs, pair)

    for pair in get_pairs_tx_mev(bundle):
        push_to_dexs(dexs, pair)

    if len(dexs) < 2:
        return None

    bundle_detail = get_bundle_detail(bundle['bundle']['hash'])
    profits_raw = get_bundle_profits_raw(bundle_detail['profits_raw'])
    if len(profits_raw) == 0:
        return None

    return {
        'tx_hash': bundle['tx_hash'],
        'bundle': bundle['bundle']['hash'],
        'block_num': bundle['blockNum'],
        # 'mev': {
        #     'profit_eth': tx['bundle']['profitEth'],
        #     'profit_margin': tx['bundle']['profitMargin'],
        #     'tipped_eth': tx['bundle']['tippedEth'],
        #     'bundle_gas_used': tx['bundle']['bundleGasUsed'],
        #     'gas_used': tx['bundle']['gasUsed'],
        #     'burned_eth': tx['bundle']['burnedEth'],
        # },
        'profits_raw': profits_raw,
        'dexs': dexs
    }


def process_generate(args):
    backtests: list[dict] = []
    bundles = read_file_json(args.p)
    for bundle in bundles:
        print(f"Process bundle {bundle['bundle']['hash']}")
        bundle = format_bundle(bundle)
        if bundle is not None:
            backtests.append(bundle)

    write_file_json(args.o, backtests)


def main():
    parser = argparse.ArgumentParser(description='Generate backtest')
    parser.add_argument('--p', type=str, required=True, help='Path file bundle json')
    parser.add_argument('--o', type=str, default='./backtest/backtest.json', help='Path file output json')
    args = parser.parse_args()
    process_generate(args)


if __name__ == '__main__':
    main()