import traceback
from typing import Tuple, Union
from src.utils import is_valid_cycle, print_log
import os
from time import sleep
from pymongo import UpdateOne
from web3 import Web3
import web3
import web3.contract
from src.mongo import MongoDb
from src.utils import read_from_file

# Swap (index_topic_1 address sender, uint256 amount0In, uint256 amount1In, uint256 amount0Out, uint256 amount1Out, index_topic_2 address to)
TOPIC_UNISWAP_V2 = bytes.fromhex("d78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822")
# Swap (index_topic_1 address sender, index_topic_2 address recipient, int256 amount0, int256 amount1, uint160 sqrtPriceX96, uint128 liquidity, int24 tick)
TOPIC_UNISWAP_V3 = bytes.fromhex("c42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67")

# Transfer (index_topic_1 address src, index_topic_2 address dst, uint256 wad)
TOPIC_ERC20_TRANSFER = bytes.fromhex("ddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef")
WETH = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"

IGNORE_TOKENS = ['0x0000000000000000000000000000000000000000']


class CycleExtractor:
    db: MongoDb
    erc20_contract: web3.contract.Contract
    w3: Web3
    w3_provider: Web3.HTTPProvider

    def init(self):
        self.db = MongoDb().connect()
        # abi_v2 = read_from_file('abi/uniswap_v2_pair.json')
        # abi_v3 = read_from_file('abi/uniswap_v3_pair.json')
        abi_erc20 = read_from_file('abi/erc20.json')

        node_url = os.getenv('ETH_HTTP_ENDPOINT') or 'http://10.7.0.58:8545'
        self.w3_provider = Web3.HTTPProvider(node_url)
        self.w3 = Web3(self.w3_provider)
        self.erc20_contract: web3.contract.Contract = self.w3.eth.contract('', abi=abi_erc20)

    def run(self):
        self.init()
        try:
            self._process()
        except KeyboardInterrupt:
            pass

    def _process(self):
        while (True):
            limit = self.db.get_info('cycles_extract_limit', 500)
            txs = list(self.db.transactions.find({'needExtractCycles': True}, {'_id': 1}).limit(limit))
            updates = []
            if (len(txs) > 0):
                print_log('CycleExtractor:', f'start processing {len(txs)} txs....')
                for tx in txs:
                    tx_hash = tx['_id']
                    try:
                        result = self.detect_cycles_2(tx_hash)
                    except Exception as e:
                        print_log('CycleExtractor detect ERROR:', f'tx={tx_hash}', e)
                        traceback.print_exc()
                        updates.append(UpdateOne(
                            {'_id': tx_hash},
                            {'$set': {'transfers': None, 'needExtractCycles': False, "cyclesError": str(e)}}))
                        continue

                    if result is None:
                        continue

                    transfers, cycles = result
                    invalid_cycles = []
                    for i, cycle in enumerate(cycles or []):
                        if not is_valid_cycle(cycle):
                            invalid_cycles.append(i)

                    set_map = {
                        'transfers': transfers,
                        'needExtractCycles': False,
                        'cycles': cycles or 'ERROR',
                    }
                    if len(invalid_cycles) > 0:
                        set_map['invalid_cycles'] = invalid_cycles

                    updates.append(UpdateOne({'_id': tx_hash}, {'$set': set_map}))

            if len(updates) > 0:
                result = self.db.transactions.bulk_write(updates)
                print_log('CycleExtractor:', 'processed result', result)

            sleep(1)

    def detect_cycles_2(self, tx_hash) -> Tuple[list, list]:
        transfers = []
        try:
            tx = self.w3.eth.get_transaction_receipt(tx_hash)
        except Exception as e:
            print_log('CycleExtractor:', f'{e}')
            return

        for log in tx.logs:
            if len(log.topics) == 0:
                continue

            event_sign = log.topics[0]
            if event_sign == TOPIC_ERC20_TRANSFER:
                token = str(log.address).lower()
                src = '0x' + str(log.topics[1].hex())[24:].lower()
                dst = '0x' + str(log.topics[2].hex())[24:].lower()
                try:
                    event = self.erc20_contract.events['Transfer']
                    args = event().process_log(log).args
                    amount = str(args.value)
                except web3.exceptions.LogTopicError as e:
                    print_log('CycleExtractor ERROR:', f'{e}, tx={tx_hash} log={log.address}')
                    amount = None
                id = len(transfers) + 1
                transfers.append({'id': id, 'from': src, 'to': dst, 'token': token, 'amount': amount})

        # Ignore send token to its contract
        new_transfers = list(filter(lambda x: x['to'] != '0x0000000000000000000000000000000000000000', transfers))

        cycles = [[]]
        search_token = WETH
        mev_addr = str(tx.to).lower()
        sender_addr = mev_addr
        while len(new_transfers) > 0:
            record = self.search_token(new_transfers, search_token, sender_addr)

            if record == None and search_token == WETH and sender_addr == mev_addr:
                print_log('CycleExtractor ERROR:', f"Didn't found send weth to another Address tx={tx_hash}")
                break

            new_transfers = self.safe_remove_item(new_transfers, record)

            if record['token'] == record['to'] and self.search_token(new_transfers, search_token, sender_addr) is None:
                # Burn token, don't append to cycle
                # print_log("Ignore ", len(cycles), ' from:', record['from'], ' to: ', record['to'], ' token: ', record['token'])
                continue

            # print_log("Cycle ", len(cycles), ' from:', record['from'], ' to: ', record['to'], ' append token: ', record['token'])
            cycles[-1].append(record)
            # Completed 1 cycle
            if len(cycles[-1]) > 1 and cycles[-1][0]['token'] == cycles[-1][-1]['token']:
                search_token = WETH
                sender_addr = mev_addr
                cycles.append([])
            # Swap token to mev but it is not WETH
            elif len(cycles[-1]) > 1 and record['to'] == mev_addr:
                # remove duplicate token if need.
                search_token = record['token']
                sender_addr = mev_addr
            else:
                search_token = None
                sender_addr = record['to']

        return transfers, cycles if len(cycles[-1]) > 0 else cycles[:-1]

    @staticmethod
    def safe_remove_item(transfers: list, record: dict):
        # remove only one item in list ...
        record = record or {}
        return list(filter(lambda x: (x['id'] != record.get('id')), transfers))

    @staticmethod
    def search_token(transfers: list, token: str, from_add: str) -> Union[dict, None]:
        try:
            if token is not None:
                record = list(filter(lambda x: x['token'] == token and x['from'] == from_add, transfers))
            else:
                record = list(filter(lambda x: x['from'] == from_add, transfers))
            if len(record) == 0:
                # handle case migrate token to other token. from: 0x0000000000000000000000000000000000000000
                record = list(filter(lambda x: x['token'] == from_add, transfers))
            # if len(record) == 0:
            #     record =  list(filter(lambda x: x['to'] == from_add and x['from'] == token, transfers))
            return record[0] if len(record) > 0 else None

        except:
            print_log("Search: FromAddr: {}, Token: {}".format(from_add, token))
            print_log(transfers)
            raise Exception()
