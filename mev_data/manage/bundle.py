import logging
import time
import queue
import threading
from os import getenv
from worker.bundle import BundleWorker, NUMBER_OF_HOURS


class BundleManager:
    def __init__(self, db):
        self.logger = logging.getLogger()
        self.db = db
        self.start_time = 0
        self.workers = []
        self.max_timestamp = 1640970000  # 2022-01-01 00:00:00
        self.num_worker = int(getenv('NUM_WORKER_BUNDLE', '4'))
        self.task_queue = queue.Queue()
        self.task_done_queue = queue.Queue()

    def check_threads_status(self):
        for worker in self.workers:
            if not worker.is_alive():
                self.logger.info(f'{worker.name} is dead')
                worker.stop()
                self.workers.remove(worker)
                new_worker = BundleWorker(db=self.db, task_queue=self.task_queue, task_done_queue=self.task_done_queue, name=worker.name)
                new_worker.start()
                self.workers.append(new_worker)
                self.logger.info(f'{new_worker.name} is started')

    def process_tasks_not_done(self) -> int:
        tasks = self.db.get_tasks_not_done()
        for task in tasks:
            start_time = task[0]
            self.task_queue.put(start_time)
        return len(tasks)

    def run(self):
        self.process_tasks_not_done()

        oldest_bundle_timestamp = self.db.get_oldest_bundle_timestamp()
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
            self.task_queue.put(self.start_time)
            worker = BundleWorker(
                db=self.db,
                task_queue=self.task_queue,
                task_done_queue=self.task_done_queue,
                name=f'Worker-bundle-{i + 1}'
            )
            worker.start()
            self.workers.append(worker)
            self.start_time -= NUMBER_OF_HOURS * 3600

        while True:
            try:
                task_done = self.task_done_queue.get(timeout=180)
                if not task_done:
                    self.check_threads_status()
                    continue

                time.sleep(1)
                self.start_time -= NUMBER_OF_HOURS * 3600
                self.task_queue.put(self.start_time)
            except queue.Empty:
                self.check_threads_status()