import json
import logging
from os import getenv
from web3 import Web3
from utils import read_file
from models import Txs, TxInputs
from uniswap_universal_router_decoder import RouterCodec
from config import UNISWAP_ROUTER_V2_ADDR, UNIVERSAL_ROUTER_ADDR


class RouterCodecWrapper:
    def __init__(self):
        self.router = RouterCodec()

    def decode_function_input(self, data):
        (func, args) = self.router.decode.function_input(data)
        args['commands'] = args['commands'].hex()
        inputs = []
        for inp in args['inputs']:
            if isinstance(inp, str):
                inputs.append(inp)
                continue

            inp: list = list(inp)
            fn_name = inp[0].fn_name
            inp[0] = fn_name
            if fn_name in ['V3_SWAP_EXACT_IN', 'V3_SWAP_EXACT_OUT']:
                inp[1]['path'] = self.router.decode.v3_path(fn_name, inp[1]['path'])
            if fn_name == 'PERMIT2_PERMIT':
                inp[1]['data'] = inp[1]['data'].hex()
            inputs.append(inp)

        args['inputs'] = inputs
        return func, args


class TxInputManager:
    def __init__(self):
        self.logger = logging.getLogger()
        self.kind = 'TxInputManager'
        self.web3 = Web3(Web3.HTTPProvider(getenv('RPC_URL')))
        self.txs = Txs()
        self.tx_inputs = TxInputs()
        self.contracts = {
            UNISWAP_ROUTER_V2_ADDR: self.web3.eth.contract(address=UNISWAP_ROUTER_V2_ADDR, abi=read_file('abi/uniswap_router_v2.json')),
            UNIVERSAL_ROUTER_ADDR: RouterCodecWrapper()
        }

    def default_serializer(self, obj):
        if isinstance(obj, bytes):
            return '0x' + obj.hex()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    def run(self):
        self.logger.info('DecodeInputManager is running')
        for key in self.contracts:
            while True:
                tx_inputs = []
                txs = self.txs.get_txs_decode_empty(key.lower(), 200)
                if not txs:
                    self.logger.info(f'{self.kind} - {key} - No txs to decode')
                    break

                for tx in txs:
                    (func, args) = self.contracts[key].decode_function_input(tx[1])
                    tx_inputs.append((tx[0], func.fn_name, json.dumps(args, default=self.default_serializer)))

                self.logger.debug(f'{self.kind} - {key} - {len(tx_inputs)} txs decoded')
                self.tx_inputs.batch_insert(tx_inputs)
