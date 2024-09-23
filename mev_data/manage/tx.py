import time
import queue
import logging
from db import Postgres
from os import getenv
from worker.tx import TxWorker


class TxManager:
    def __init__(self, db):
        self.logger = logging.getLogger()
        self.db: Postgres = db
        self.workers = []
        self.num_worker = int(getenv('NUM_WORKER_TX', '2'))
        self.task_queue = queue.Queue()
        self.task_done_queue = queue.Queue()

    def check_threads_status(self):
        for worker in self.workers:
            if not worker.is_alive():
                self.logger.info(f'{worker.name} is dead')
                worker.stop()
                self.workers.remove(worker)
                new_worker = TxWorker(
                    db=self.db,
                    task_queue=self.task_queue,
                    task_done_queue=self.task_done_queue,
                    name=worker.name
                )
                new_worker.start()
                self.workers.append(new_worker)
                self.logger.info(f'{new_worker.name} is started')

    def put_txs_to_queue(self):
        txs = [tx[0] for tx in self.db.get_txs_empty()]
        if txs is None or len(txs) == 0:
            time.sleep(30)
            return self.put_txs_to_queue()
        self.task_queue.put(txs)

    def run(self):
        # start worker threads
        for i in range(self.num_worker):
            worker = TxWorker(
                db=self.db,
                task_queue=self.task_queue,
                task_done_queue=self.task_done_queue,
                name=f'Worker-tx-{i+1}'
            )
            worker.start()
            self.put_txs_to_queue()
            self.workers.append(worker)

        while True:
            try:
                task_done = self.task_done_queue.get(timeout=180)
                if not task_done:
                    self.check_threads_status()
                    continue

                self.put_txs_to_queue()
            except queue.Empty:
                self.check_threads_status()
