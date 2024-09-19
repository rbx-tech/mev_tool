import logging
import threading
from os import getenv
from utils.rpc import RPC


class TxWorker(threading.Thread):
    def __init__(self, db, task_queue, task_done_queue, *args, **kwargs):
        threading.Thread.__init__(self, *args, **kwargs)
        self.db = db
        self.rpc: RPC = RPC(getenv('RPC_URL'))
        self.logger = logging.getLogger()
        self.task_queue = task_queue
        self.task_done_queue = task_done_queue

    def run(self):
        self.logger.info(f'{self.name} started')
        while True:
            tx_hashes = self.task_queue.get()
            if tx_hashes is None or len(tx_hashes) == 0:
                self.logger.info(f'{self.name} stopped')
                break
            try:
                txs = self.rpc.batch_request_get_tx_by_hashes(tx_hashes)
                self.db.batch_insert_txs(txs)
                self.task_done_queue.put(True)
            except Exception as err:
                self.logger.error(f'{self.name} - {err}')
                self.task_queue.put(tx_hashes)
                self.task_done_queue.put(False)
