import requests
import eth_abi
from hexbytes import HexBytes
from utils.helper import decode_rs

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

    """
    Get pairs by index range
    Returns:
        [[pair, token0, token1]]
    """
    def get_pairs_by_index_range(self, factory_address: str, index_start: int, index_end: int):
        data: bytes = eth_abi.encode(['address', 'uint256', 'uint256'], [factory_address, index_start, index_end])
        data_hex: str = '0xab2217e4' + data.hex()
        result = self.eth_call('0x5EF1009b9FCD4fec3094a5564047e190D72Bd511', data_hex)
        pairs = eth_abi.decode(['address[3][]'], HexBytes(result))[0]
        return [[pair[2], pair[0], pair[1]] for pair in pairs]

    def get_tx_receipt(self, tx_hash: str):
        body = RPC.make_body('eth_getTransactionReceipt', [tx_hash])
        return requests.post(self.rpc_url, json=body).json()['result']

    def get_symbols_by_pairs(self, pairs: list):
        if len(pairs) == 0:
            return {}

        body = []
        for pair in pairs:
            token0 = pair['token0']
            token1 = pair['token1']
            if token0['symbol'] == '':
                body.append(RPC.make_body_call(token0['address'], '0x95d89b41', 'latest', token0['address']))
            if token1['symbol'] == '':
                body.append(RPC.make_body_call(token1['address'], '0x95d89b41', 'latest', token1['address']))

        res = requests.post(self.rpc_url, json=body).json()

        result = {}
        for r in res:
            if 'error' in r:
                print(f'Pair {r["id"]} error: {r["error"]}')
                continue

            try:
                symbol = eth_abi.decode(['string'], HexBytes(r['result']))[0]
                result[r['id']] = symbol
                continue
            except Exception:
                pass

            try:
                symbol = eth_abi.decode(['bytes32'], HexBytes(r['result']))[0].decode('utf-8').rstrip('\x0000')
            except Exception:
                symbol = 'ERROR'
            result[r['id']] = symbol

        return result

    def get_rs_at_tx(self, block_hash: str, tx_idx: int, pair_address: str):
        body = self.make_body(
            'debug_storageRangeAt',
            [
                block_hash,
                tx_idx,
                pair_address,
                '0x0000000000000000000000000000000000000000000000000000000000000000',
                6
            ]
        )

        res = requests.post(self.rpc_url, json=body).json()
        storage = res['result']['storage']
        if storage is None:
            return None

        for item in storage:
            if storage[item]['key'] == '0x0000000000000000000000000000000000000000000000000000000000000008':
                return decode_rs(int(storage[item]['value'], 16))