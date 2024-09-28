import logging
from os import getenv
from utils.rpc import RPC
from utils import chunk_list
from models import Bundles, Tasks, TxLogs


class TxLogManager:
    def __init__(self):
        self.logger = logging.getLogger()
        self.kind = 'tx_log'
        self.tasks = Tasks()
        self.bundles = Bundles()
        self.tx_logs = TxLogs()
        self.rpc = RPC(getenv('RPC_URL'))

    def run(self):
        self.logger.info('TxLogManager is running')
        page = 1
        limit = 500

        task = self.tasks.get_by_kind(self.kind)
        if task:
            page = task[2]['page'] + 1
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
        searcher_hashes = [tx_hash for tx in searcher_txs for tx_hash in tx[0]]
        chunks = chunk_list(searcher_hashes, 50)
        for chunk in chunks:
            tx_receipts = self.process_tx_receipts(chunk)
            self.tx_logs.batch_insert(tx_receipts)

    def process_tx_receipts(self, searcher_hashes: list[str]):
        result = []
        receipts = self.rpc.batch_get_tx_receipts(searcher_hashes)
        for receipt in receipts:
            if receipt is None:
                continue
            for log in receipt.get('logs', []):
                result.append((
                    log['transactionHash'],
                    log['address'],
                    log['topics'][0][:10],
                    log['topics'],
                    log['data'],
                    int(log['logIndex'], 16),
                    log['removed']
                ))
        return result
