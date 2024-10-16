from collections import defaultdict
import os
from time import sleep
from pymongo import UpdateOne
from web3 import Web3
import web3
import web3.contract
from src.mongo import MongoDb
from src.utils import chunk_list, read_from_file

# Swap (index_topic_1 address sender, uint256 amount0In, uint256 amount1In, uint256 amount0Out, uint256 amount1Out, index_topic_2 address to)
TOPIC_UNISWAP_V2 = bytes.fromhex("d78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822")
# Swap (index_topic_1 address sender, index_topic_2 address recipient, int256 amount0, int256 amount1, uint160 sqrtPriceX96, uint128 liquidity, int24 tick)
TOPIC_UNISWAP_V3 = bytes.fromhex("c42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67")

# Transfer (index_topic_1 address src, index_topic_2 address dst, uint256 wad)
TOPIC_ERC20_TRANSFER = bytes.fromhex("ddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef")
WETH = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"


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
            txs = list(self.db.transactions.find({'transfers': {'$exists': 0}, 'tags': 'searcher', 'types': 'arbitrage'}, {'_id': 1}).limit(limit))
            updates = []
            if (len(txs) > 0):
                print('CycleExtractor:', f'start processing {len(txs)} txs....')
                for tx in txs:
                    tx_hash = tx['_id']
                    result = self.detect_cycles(tx_hash)
                    if result is None:
                        updates.append(UpdateOne(
                            {'_id': tx_hash},
                            {'$set': {'transfers': None, 'cycles': None}}))
                        continue
                    cycles, transfers = result

                    updates.append(UpdateOne(
                        {'_id': tx_hash},
                        {
                            '$set': {
                                'transfers': transfers,
                                'cycles': cycles,
                            }
                        }))

            if len(updates) > 0:
                result = self.db.transactions.bulk_write(updates)
                print('CycleExtractor:', 'processed result', result)

            sleep(1)

    def detect_cycles(self, tx_hash):
        try:
            tx_trace = self.w3_provider.make_request('trace_transaction', [tx_hash])
            tx = self.w3.eth.get_transaction(tx_hash)
        except Exception as e:
            print('CycleExtractor:', f'{e}')
            return

        to_addr = str(tx.to).lower()
        transfers = []
        mev_transfers = defaultdict(lambda: [])
        i = 0
        tokens = []
        for trace in tx_trace['result']:
            action = trace['action']
            try:
                func, args = self.erc20_contract.decode_function_input(action['input'])
                if 'transfer' not in func.fn_name:
                    continue
                if args.get('sender'):
                    src = str(args['sender']).lower()
                else:
                    src = str(action['from']).lower()
                dst = str(args['recipient']).lower()
                token = str(action['to']).lower()
                tokens.append(token)
                amount = str(args['amount'])
                info = {'from': src, 'to': dst, 'token': token, 'amount': amount}
                if src not in tokens:
                    if to_addr == src:
                        mev_transfers[token].append((i, -1, amount))
                    if to_addr == dst:
                        mev_transfers[token].append((i, +1, amount))
                transfers.append(info)
                i += 1
            except Exception as e:
                continue

        cycles = []
        # for k in mev_transfers.keys():
        chunks = chunk_list(mev_transfers[WETH], 2)
        for c in chunks:
            if len(c) != 2:
                continue
            i1, m1, amount1 = c[0]
            i2, m2, amount2 = c[1]
            if m1*int(amount1) + m2 * int(amount2) > 0:
                cycles.append(transfers[i1:i2 + 1])
        return cycles, transfers

    def detect_cycle_2(self, tx_hash):
        transfers = []
        try:
            tx = self.w3.eth.get_transaction_receipt(tx_hash)
        except Exception as e:
            print('CycleExtractor:', f'{e}')
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
                    print('CycleExtractor ERROR:', f'{e}, tx={tx_hash} log={log.address}')
                    amount = None
                id = len(transfers) + 1
                transfers.append({'id': id, 'from': src, 'to': dst, 'token': token, 'amount': amount})

        cycle = [[]]
        search_token = WETH
        mev_addr = str(tx.to).lower()
        sender_addr = mev_addr
        while len(transfers) > 0:
            record = self.search_token(transfers, search_token, sender_addr)
            print("Cycle ", len(cycle), ' append token: ', record['token'], ' from:', record['from'])
            cycle[-1].append(record['token'])
            transfers = self.safe_remove_item(transfers, record)
            # Completed 1 cycle
            if len(cycle[-1]) > 1 and cycle[-1][0] == cycle[-1][-1]:
                search_token = WETH
                sender_addr = mev_addr
                cycle.append([])
            # Swap token to mev but it is not WETH
            elif len(cycle[-1]) > 1 and record['to'] == mev_addr:
                # remove duplicate token if need.
                search_token = record['token']
                sender_addr = mev_addr
            else:
                search_token = None
                sender_addr = record['to']
        return cycle

    def safe_remove_item(self, transfers, record):
        # remove only one item in list ...
        return list(filter(lambda x: (x['id'] != record['id']), transfers))

    def search_token(self, transfers: list, token: str, from_add: str):
        try:
            if token is not None:
                return list(filter(lambda x: x['token'] == token and x['from'] == from_add, transfers))[0]
            return list(filter(lambda x: x['from'] == from_add, transfers))[0]
        except:
            print(transfers)
            raise Exception()
