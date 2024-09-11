import requests
import time
from abc import ABC, abstractmethod
from utils.helper import write_file_json

TOKEN = '944b560e76f53abf0739468966998887'
PATH_UNISWAP_V2 = './pairs/uniswap_v2.json'
PATH_SUSHI_V2 = './pairs/sushi_v2.json'
PATH_SHIBASWAP = 'pairs/shibaswap_v2.json'


class CrawlDexV2(ABC):
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
            'Authorization': 'Bearer ' + TOKEN,
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


class UniSwapV2(CrawlDexV2):
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
    pass


class SushiSwap(CrawlDexV2):
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


def main():
    # UniSwapV2(
    #     'QmZzsQGDmQFbzYkv2qx4pVnD6aVnuhKbD3t1ea7SAvV7zE',
    #     {
    #         'router_address': '0x7a250d5630b4cf539739df2c5dacb4c659f2488d',
    #         'factory_address': '0x5c69bee701ef814a2b6a3edd4b1652cb9cc5aa6f',
    #     },
    #     PATH_UNISWAP_V2
    # ).process()
    #
    # SushiSwap(
    #     'Qmc9f8kuGoE8D3ME38ns2MCodYtSA4gHgyFRojdyK88tL6',
    #     {
    #         "router_address": "0xd9e1ce17f2641f24ae83637ab66a2cca9c378b9f",
    #         "factory_address": "0xc0aee478e3658e2610c5f7a4a2e1777ce9e4f2ac",
    #     },
    #     PATH_SUSHI_V2,
    # ).process()

    ShibaSwap(
        'QmeSR4qJNqeDiBJqHScKJeUrMFNwuK62FMdGtWNj4i2x2f',
        {
            "router_address": "",
            "factory_address": "0x115934131916C8b277DD010Ee02de363c09d037c"
        },
        PATH_SHIBASWAP,
    ).process()


if __name__ == '__main__':
    main()
