import requests
import eth_abi
from hexbytes import HexBytes


class RPC:
    def __init__(self, rpc_url: str):
        self.rpc_url = rpc_url

    @staticmethod
    def make_body(method: str, params: list, id: str = '1'):
        return {
            'jsonrpc': '2.0',
            'method': method,
            'params': params,
            'id': id,
        }

    @staticmethod
    def make_body_call(to: str, data: str, block_number: str = 'latest', id: str = '1'):
        return RPC.make_body('eth_call', [{'to': to, 'data': data}, block_number], id)

    def eth_call(self, to: str, data: str):
        body = RPC.make_body_call(to, data)
        res = requests.post(self.rpc_url, json=body)
        return res.json()['result']

    def get_all_pairs_length(self, factory_address: str):
        data_hex: str = '0x574f2ba3'
        result = self.eth_call(factory_address, data_hex)
        return eth_abi.decode(['uint256'], HexBytes(result))[0]

    def get_tx_receipt(self, tx_hash: str):
        body = RPC.make_body('eth_getTransactionReceipt', [tx_hash])
        return requests.post(self.rpc_url, json=body).json()['result']

    def batch_request_get_tx_by_hashes(self, hashes: list):
        body = [self.make_body('eth_getTransactionByHash', [h], h) for h in hashes]
        res = requests.post(self.rpc_url, json=body)
        res.raise_for_status()
        return [r['result'] for r in res.json()]
