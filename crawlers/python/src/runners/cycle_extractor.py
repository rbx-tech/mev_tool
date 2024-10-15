import os
from time import sleep
from pymongo import UpdateOne
from web3 import Web3
import web3
import web3.contract
from src.mongo import MongoDb
import networkx as nx
from src.utils import read_from_file

# Swap (index_topic_1 address sender, uint256 amount0In, uint256 amount1In, uint256 amount0Out, uint256 amount1Out, index_topic_2 address to)
TOPIC_UNISWAP_V2 = bytes.fromhex("d78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822")
# Swap (index_topic_1 address sender, index_topic_2 address recipient, int256 amount0, int256 amount1, uint160 sqrtPriceX96, uint128 liquidity, int24 tick)
TOPIC_UNISWAP_V3 = bytes.fromhex("c42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67")

# Transfer (index_topic_1 address src, index_topic_2 address dst, uint256 wad)
TOPIC_ERC20_TRANSFER = bytes.fromhex("ddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef")


class CycleExtractor:
    db: MongoDb
    erc20_contract: web3.contract.Contract
    w3: Web3

    def run(self):
        self.db = MongoDb().connect()

        # abi_v2 = read_from_file('abi/uniswap_v2_pair.json')
        # abi_v3 = read_from_file('abi/uniswap_v3_pair.json')
        abi_erc20 = read_from_file('abi/erc20.json')

        node_url = os.getenv('ETH_HTTP_ENDPOINT') or 'http://10.7.0.58:8545'
        self.w3 = Web3(Web3.HTTPProvider(node_url))
        self.erc20_contract: web3.contract.Contract = self.w3.eth.contract('', abi=abi_erc20)
        try:
            self._process()
        except KeyboardInterrupt:
            pass

    def _process(self):
        while (True):
            limit = self.db.get_info('cycles_extract_limit', 500)
            txs = list(self.db.transactions.find({'transfers': {'$exists': 0}}, {'_id': 1}).limit(limit))
            updates = []
            if (len(txs) > 0):
                print('CycleExtractor:', f'start processing {len(txs)} txs....')
                for tx in txs:
                    tx_hash = tx['_id']
                    try:
                        tx = self.w3.eth.get_transaction_receipt(tx_hash)
                    except Exception as e:
                        print('CycleExtractor:', f'{e}')
                        updates.append(UpdateOne(
                            {'_id': tx_hash},
                            {'$set': {'transfers': None, 'cycles': None}}))
                        continue

                    G = nx.DiGraph()
                    transfers = []
                    for log in tx.logs:
                        if len(log.topics) == 0:
                            continue

                        event_sign = log.topics[0]
                        if event_sign == TOPIC_ERC20_TRANSFER:
                            token = '0x' + str(log.address).lower()
                            src = '0x' + str(log.topics[1].hex())[24:].lower()
                            dst = '0x' + str(log.topics[2].hex())[24:].lower()
                            try:
                                event = self.erc20_contract.events['Transfer']
                                args = event().process_log(log).args
                                amount = str(args.value)
                            except web3.exceptions.LogTopicError as e:
                                print('CycleExtractor ERROR:', f'{e}, tx={tx_hash} log={log.address}')
                                amount = None
                            transfers.append({'from': src, 'to': dst, 'token': token, 'amount': amount})
                            G.add_edge(src, dst)

                    cycles = list(nx.simple_cycles(G))
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
