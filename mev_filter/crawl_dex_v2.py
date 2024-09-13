import time
import requests
from abc import ABC, abstractmethod
from utils.helper import read_file, chunk_list,write_file_json
from utils.rpc import RPC

RPC_URL = 'https://rpc.ankr.com/eth'
TOKEN_THE_GRAPH = '944b560e76f53abf0739468966998887'
PATH_UNISWAP_V2 = 'pairs/uniswap_v2.json'
PATH_SUSHI_V2 = 'pairs/sushi_v2.json'
PATH_SHIBASWAP = 'pairs/shibaswap_v2.json'
PATH_CRO_SWAP = 'pairs/cro_swap.json'
PATH_PANCAKE_SWAP = 'pairs/pancake_swap.json'


class CrawlDexRPC:
    def __init__(self, factory_address: str, info: dict, output_path: str = ''):
        self.rpc = RPC(RPC_URL)
        self.factory_address = factory_address
        self.info = info
        self.output_path = output_path
        self.symbol_map = {}

    def cache_symbols(self, symbols: dict):
        for key, value in symbols.items():
            self.symbol_map[key] = value

    def fill_symbol_cache(self, pairs):
        result = []
        for pair in pairs:
            pair_address = pair[0] if isinstance(pair, list) else pair['address']
            token0 = pair[1] if isinstance(pair, list) else pair['token0']['address']
            token1 = pair[2] if isinstance(pair, list) else pair['token1']['address']
            result.append({
                'address': pair_address,
                'token0': {
                    'address': token0,
                    'symbol': self.symbol_map.get(token0, '')
                },
                'token1': {
                    'address': token1,
                    'symbol': self.symbol_map.get(token1, '')
                }
            })
        return result

    def fill_symbols_to_pairs(self, pairs, symbols):
        for pair in pairs:
            if pair['token0']['symbol'] == '':
                pair['token0']['symbol'] = symbols[pair['token0']['address']]
                self.symbol_map[pair['token0']['address']] = pair['token0']['symbol']


    def process(self):
        result = []
        pairs_length = self.rpc.get_all_pairs_length(self.factory_address)
        for i in range(0, pairs_length, 50):
            print(f"Processing {i} -> {min(i + 50, pairs_length)} of {pairs_length}")
            pairs = self.rpc.get_pairs_by_index_range(self.factory_address, i, i + 50)
            pairs = self.fill_symbol_cache(pairs)
            for chunk in chunk_list(pairs, 5):
                symbols = self.rpc.get_symbols_by_pairs(chunk)
                self.cache_symbols(symbols)
                chunk = self.fill_symbol_cache(chunk)
                result.extend(chunk)
            self.write_pairs(result)

    def write_pairs(self, pairs):
        write_file_json(self.output_path, {
            **self.info,
            'pairs': pairs
        })


class CrawlDexTheGraph(ABC):
    def __init__(self, graph_id: str, info: dict, output_path: str, limit: int = 500):
        self.graph_id = graph_id
        self.info = info
        self.output_path = output_path
        self.limit = limit

    def process(self):
        result = []
        skip = 0
        class_name = self.__class__.__name__
        while True:
            print(f"Crawling {class_name} pair, skip:", skip)
            res = self.request_thegraph(self.graph_id, self.query(skip))
            if res is None:
                break

            pairs = res['data']['pairs']
            if len(pairs) == 0:
                break

            pairs = list(map(self.rename_key, pairs))
            result.extend(pairs)
            skip += 500
            time.sleep(0.5)

        self.write_pairs({
            "router_address": self.info['router_address'],
            "factory_address": self.info['factory_address'],
            "pairs": result
        })

    @abstractmethod
    def query(self, skip: int) -> str:
        pass

    @abstractmethod
    def rename_key(self, pair: dict) -> dict:
        pass

    def request_thegraph(self, graph_id: str, query: str):
        headers = {
            'Authorization': 'Bearer ' + TOKEN_THE_GRAPH,
            'Origin': 'https://thegraph.com'
        }

        response = requests.post(
            f"https://gateway.thegraph.com/api/deployments/id/{graph_id}",
            headers=headers, json={"query": query}
        )

        if response.status_code != 200:
            print(f"Request fail: {response.status_code}")
            return None
        return response.json()

    def write_pairs(self, pairs):
        write_file_json(self.output_path, pairs)


class UniSwapV2(CrawlDexTheGraph):
    def __init__(self, graph_id: str):
        info = {
            'router_address': '0x7a250d5630b4cf539739df2c5dacb4c659f2488d',
            'factory_address': '0x5c69bee701ef814a2b6a3edd4b1652cb9cc5aa6f'
        }
        super().__init__(
            graph_id,
            info,
            PATH_UNISWAP_V2
        )

    def query(self, skip: int) -> str:
        return f"""
            {{
              pairs(first: {self.limit}, skip: {skip}) {{
                id
                token0 {{
                  id
                  symbol
                }}
                token1 {{
                  id
                  symbol
                }}
              }}
            }}
        """

    def rename_key(self, pair: dict) -> dict:
        return {
            'address': pair['id'],
            'token0': {
                'address': pair['token0']['id'],
                'symbol': pair['token0']['symbol']
            },
            'token1': {
                'address': pair['token1']['id'],
                'symbol': pair['token1']['symbol']
            }
        }


class ShibaSwap(UniSwapV2):
    def __init__(self, graph_id: str):
        info = {
            'router_address': '0x03f7724180aa6b939894b5ca4314783b0b36b329',
            'factory_address': '0x115934131916C8b277DD010Ee02de363c09d037c'
        }
        super(UniSwapV2, self).__init__(
            graph_id,
            info,
            PATH_SHIBASWAP
        )


class SushiSwap(CrawlDexTheGraph):
    def __init__(self, graph_id: str):
        info = {
            'router_address': '0xd9e1ce17f2641f24ae83637ab66a2cca9c378b9f',
            'factory_address': '0xc0aee478e3658e2610c5f7a4a2e1777ce9e4f2ac'
        }
        super().__init__(graph_id, info, PATH_SUSHI_V2)

    def query(self, skip: int):
        return f"""
            {{
              pairs: liquidityPools(first: {self.limit}, skip: {skip}) {{
                id
                inputTokens {{
                  id
                  symbol
                }}
              }}
            }}
        """

    def rename_key(self, pair: dict) -> dict:
        return {
            'address': pair['id'],
            'token0': {
                'address': pair['inputTokens'][0]['id'],
                'symbol': pair['inputTokens'][0]['symbol']
            },
            'token1': {
                'address': pair['inputTokens'][1]['id'],
                'symbol': pair['inputTokens'][1]['symbol']
            }
        }


class UniswapV2RPC(CrawlDexRPC):
    def __init__(self):
        factory_address = '0x5c69bee701ef814a2b6a3edd4b1652cb9cc5aa6f'
        info = {
            'router_address': '0x7a250d5630b4cf539739df2c5dacb4c659f2488d',
            'factory_address': factory_address
        }
        super().__init__(factory_address, info, './pairs/uniswap_v2_rpc.json')

class CroSwap(CrawlDexRPC):
    def __init__(self):
        factory_address = '0x9deb29c9a4c7a88a3c0257393b7f3335338d9a9d'
        info = {
            'router_address': '0xceb90e4c17d626be0facd78b79c9c87d7ca181b3',
            'factory_address': factory_address
        }
        super().__init__(factory_address, info, PATH_CRO_SWAP)


class PancakeSwap(CrawlDexRPC):
    def __init__(self):
        factory_address = '0x1097053fd2ea711dad45caccc45eff7548fcb362'
        info = {
            'router_address': '0xeff92a263d31888d860bd50809a8d171709b7b1c',
            'factory_address': factory_address
        }
        super().__init__(factory_address, info, PATH_PANCAKE_SWAP)

def main():
    UniswapV2RPC().process()
    # UniSwapV2('QmZzsQGDmQFbzYkv2qx4pVnD6aVnuhKbD3t1ea7SAvV7zE').process()
    # SushiSwap('Qmc9f8kuGoE8D3ME38ns2MCodYtSA4gHgyFRojdyK88tL6').process()
    # ShibaSwap('QmeSR4qJNqeDiBJqHScKJeUrMFNwuK62FMdGtWNj4i2x2f').process()
    # CroSwap().process()
    # PancakeSwap().process()


if __name__ == '__main__':
    main()
