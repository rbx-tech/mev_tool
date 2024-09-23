import logging
from os import getenv
from utils.rpc import RPC
from models import Bundles, Tasks, TxFilters
from utils.helper import chunk_list, read_file_json


class TxFilterManager:
    def __init__(self):
        self.logger = logging.getLogger()
        self.kind = 'tx_filter'
        self.tasks = Tasks()
        self.bundles = Bundles()
        self.tx_filters = TxFilters()
        self.rpc = RPC(getenv('RPC_URL'))
        self.address_map = read_file_json('config/list_address.json')
        self.tokens = read_file_json('config/tokens_eth.json')
        self.method_map = {
            '0x908fb5ee': "Balancer",
            '0x2170c741': "Balancer",
            '0x0d7d75e0': "Balancer FlashLoan",
            '0xc42079f9': "UniswapV3"
        }

    def run(self):
        self.logger.info('FilterManager is running')
        page = 1
        limit = 50

        task = self.tasks.get_by_kind(self.kind)
        if task:
            page = task[2]['page']
            limit = task[2]['limit']

        while True:
            self.logger.info(f'Processing page {page}')
            searcher_txs = self.bundles.get_paginated(page, limit)
            if not searcher_txs:
                self.logger.info('No more bundles to process')
                break
            self.process_searcher_txs(searcher_txs)
            self.tasks.create(self.kind, {'page': page, 'limit': limit})
            page += 1

    def process_searcher_txs(self, searcher_txs: list[str]):
        searcher_hashes = []
        for tx in searcher_txs:
            searcher_hashes.extend(tx[0])

        chunks = chunk_list(searcher_hashes, 50)
        for chunk in chunks:
            tx_filters = self.process_filter(chunk)
            self.tx_filters.batch_insert(tx_filters)

    def process_filter(self, searcher_hashes: list[str]):
        result = []

        receipts = self.rpc.batch_get_tx_receipts(searcher_hashes)
        for receipt in receipts:
            if receipt['status'] == '0x1':
                tx_hash = receipt['transactionHash']
                temp = {
                    'tx_hash': tx_hash,
                    'is_v3': False,
                    'token_gt_2': False,
                    'tokens': set(),
                    'addresses': [],
                    'address_names': []
                }

                logs = receipt['logs']
                for log in logs:
                    addr = log['address']
                    if addr in self.address_map:
                        if addr not in temp['addresses']:
                            temp['address_names'].append(self.address_map[addr])
                            temp['addresses'].append(addr)
                    if log['topics'][0][:10] in self.method_map:
                        if addr not in temp['addresses']:
                            temp['address_names'].append(self.method_map[log['topics'][0][:10]])
                            temp['addresses'].append(addr)
                    if addr in self.tokens:
                        temp['tokens'].add(addr)

                temp['tokens'] = list(temp['tokens'])
                if len(temp['tokens']) > 2:
                    temp['token_gt_2'] = True
                if 'UniSwapV3' in temp['address_names']:
                    temp['is_v3'] = True
                result.append(temp)
            else:
                self.logger.debug(f'Tx {receipt["transactionHash"]} failed')

        return result
