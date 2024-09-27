import logging
from utils import chunk_list
from models import Bundles, Tasks, Txs


class TxKindManager:
    def __init__(self):
        self.logger = logging.getLogger()
        self.kind = 'tx_kind'
        self.tasks = Tasks()
        self.bundles = Bundles()
        self.txs = Txs()

    def run(self):
        self.logger.info('TxKindManager is running')
        page = 1
        limit = 500

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
        searcher_hashes = [tx_hash for tx in searcher_txs for tx_hash in tx[0]]
        chunks = chunk_list(searcher_hashes, 500)
        for chunk in chunks:
            self.txs.update_kind(chunk)
