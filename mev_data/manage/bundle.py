import logging
import time
import queue
from os import getenv
from models import Tasks, Bundles, Txs
from worker.bundle import BundleWorker


class BundleManager:
    def __init__(self):
        self.logger = logging.getLogger()
        self.tasks = Tasks()
        self.bundles = Bundles()
        self.txs = Txs()
        self.start_time = 0
        self.workers = []
        self.max_timestamp = 1640970000  # 2022-01-01 00:00:00
        self.num_worker = int(getenv('NUM_WORKER_BUNDLE', '4'))
        self.num_of_hours = int(getenv('NUMBER_OF_HOURS', '6'))
        self.task_queue = queue.Queue()
        self.task_done_queue = queue.Queue()

    def check_threads_status(self):
        for worker in self.workers:
            if not worker.is_alive():
                self.logger.info(f'{worker.name} is dead')
                self.workers.remove(worker)
                new_worker = BundleWorker(task_queue=self.task_queue, task_done_queue=self.task_done_queue, name=worker.name)
                new_worker.start()
                self.workers.append(new_worker)
                self.logger.info(f'{new_worker.name} is started')

    def process_tasks_not_done(self) -> int:
        tasks = self.tasks.get_not_done()
        for task in tasks:
            start_time = task[0]
            self.task_queue.put(self.get_time_range(start_time))
        return len(tasks)

    def run(self):
        self.process_tasks_not_done()

        oldest_bundle_timestamp = self.bundles.get_oldest_bundle_timestamp()
        if not oldest_bundle_timestamp:
            self.logger.info('No bundle found in database')
            self.start_time = int(time.time())
        else:
            self.start_time = oldest_bundle_timestamp[0][0]

        if self.start_time <= self.max_timestamp:
            self.logger.info('MAX_TIMESTAMP reached')
            return

        # start worker threads
        for i in range(self.num_worker):
            self.task_queue.put(self.get_time_range())
            worker = BundleWorker(
                task_queue=self.task_queue,
                task_done_queue=self.task_done_queue,
                name=f'Worker-bundle-{i + 1}'
            )
            worker.start()
            self.workers.append(worker)

        self.loop()

    def loop(self):
        while True:
            try:
                task_done = self.task_done_queue.get(timeout=180)
                if not task_done:
                    self.check_threads_status()
                    continue
                if isinstance(task_done, tuple):
                    task_id, bundles = task_done
                    self.bundles.batch_insert(bundles)
                    self.txs.batch_insert_txs_empty(bundles)
                    self.tasks.update_done(task_id, len(bundles))
                    self.logger.info(f'Inserted {len(bundles)} bundles')
                time.sleep(1)

                self.task_queue.put(self.get_time_range())
            except queue.Empty:
                self.check_threads_status()

    def get_time_range(self, start_time=None):
        start_time = None if start_time is None else start_time
        end_time = 0
        if start_time is None:
            start_time = self.start_time - (self.num_of_hours * 3600)
            end_time = self.start_time
            self.start_time = start_time
        else:
            start_time = start_time - (self.num_of_hours * 3600)
            end_time = start_time

        task_id = self.tasks.create(start_time, end_time)
        return task_id, start_time, end_time
