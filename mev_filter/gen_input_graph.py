from utils.helper import read_file_json, write_file_json
from utils.rpc import RPC
import argparse
import random
import os
import copy
import hashlib
import networkx as nx


URL_RPC = 'http://10.7.0.58:8545'
TOKEN_ETH = list(read_file_json('config/tokens_eth.json').keys())
MAX_TOKEN = 10

rpc = RPC(URL_RPC)


class Factory:
    def __init__(self):
        self.pair_map = {}
        self.dexs = {}
        self.graph = nx.Graph()

    @staticmethod
    def get_pair_key(token0 :str, token1: str):
        key_str = '_'.join(sorted([token0.lower(), token1.lower()]))
        key_hash = hashlib.md5(key_str.encode()).hexdigest()
        return key_hash

    def get_pair(self, pair_address: str):
        return copy.deepcopy(self.pair_map.get(pair_address))

    def get_random_edges_with_dex(self, node: str, n: int, dex: str):
        edges = []
        for neighbor in self.graph.neighbors(node):
            edge_data = self.graph.get_edge_data(node, neighbor)
            if edge_data is not None and dex in edge_data.get('dexs', []):
                idx_dex = edge_data['dexs'].index(dex)
                edges.append(edge_data['pairs'][idx_dex])

        return random.sample(edges, min(n, len(edges)))

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
            pair = {
                'address': pair['address'],
                'dex': file_name,
                'token0': {
                    **pair['token0'],
                    'reserve': '0'
                },
                'token1': {
                    **pair['token1'],
                    'reserve': '0'
                },
            }

            self.init_edge(
                pair['token0']['address'],
                pair['token1']['address'],
                pair['address'],
                file_name
            )

            self.pair_map[pair['address']] = pair

    def init_edge(self, token0: str, token1: str, address:str, dex: str):
        edge_data = self.graph.get_edge_data(token0, token1)
        if edge_data is None:
            self.graph.add_edge(token0, token1, pairs=[address], dexs=[dex])
        else:
            edge_data['pairs'].append(address)
            edge_data['dexs'].append(dex)


factory = Factory()
factory.load('./pairs')


def process_pairs(bundle, pairs):
    result = []

    for p in pairs:
        pair = factory.get_pair(p)
        rs = rpc.get_rs_at_tx(bundle['blockHash'], bundle['tx']['transactionIndex'], p)
        if rs is not None:
            pair['token0']['reserve'] = str(rs[0])
            pair['token1']['reserve'] = str(rs[1])
            result.append(pair)

    return result


def process_bundle(bundles):
    result = []
    for b in bundles:
        dexs = set()
        pairs = set()
        tokens = set()
        searcher_receipt = rpc.get_tx_receipt(b['searcher_tx'])
        for l in searcher_receipt['logs']:
            addr = l['address']
            pair = factory.get_pair(addr)
            if pair is not None:
                dexs.add(pair['dex'])
                pairs.add(addr)
                tokens.add(pair['token0']['address'])
                tokens.add(pair['token1']['address'])

        if len(dexs) > 2:
            raise Exception('Dexs > 2')

        list_dex = list(dexs)
        list_token = list(tokens)
        for dex in list_dex:
            pairs.update(factory.get_random_edges_with_dex(
                list_token[0],
                int((MAX_TOKEN - 2) / 2),
                dex
            ))

            pairs.update(factory.get_random_edges_with_dex(
                list_token[1],
                int((MAX_TOKEN - 2) / 2),
                dex
            ))

        result.append({
            'bundle_hash': b['bundle']['hash'],
            'pairs': process_pairs(b, list(pairs))
        })

    write_file_json('input_graph.json', result)


def main(args):
    bundles = read_file_json(args.p)
    process_bundle(bundles)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='A simple CLI tool.')
    parser.add_argument('--p', type=str, help='Path file bundles', required=True)
    args = parser.parse_args()

    main(args)