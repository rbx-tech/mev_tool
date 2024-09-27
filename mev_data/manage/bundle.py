import logging
import time
import queue
from os import getenv
from config import LIBMEV_MIN_TIMESTAMP
from models import Bundles, Txs, BundleTasks
from worker.bundle import BundleWorker


class BundleManager:
    def __init__(self):
        self.logger = logging.getLogger()
        self.bundle_tasks = BundleTasks()
        self.bundles = Bundles()
        self.txs = Txs()
        self.start_time = int(time.time())
        self.workers = []
        self.time_range = []
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
        tasks = self.bundle_tasks.get_not_done()
        for task in tasks:
            start_time = task[0]
            self.task_queue.put(self.get_time_range(start_time))
        return len(tasks)

    def put_task(self):
        if self.task_queue.qsize() <= self.num_worker:
            time_range = self.get_time_range()
            if time_range is None:
                return None
            self.task_queue.put(time_range)
        return self.task_queue.qsize()

    def run(self):
        self.process_tasks_not_done()
        lastest_timestamp = self.bundles.get_latest_bundle_timestamp()
        if lastest_timestamp:
            time_now = int(time.time())
            self.time_range.append((time_now, lastest_timestamp))
            oldest_timestamp = self.bundles.get_oldest_bundle_timestamp()

            if oldest_timestamp > LIBMEV_MIN_TIMESTAMP:
                self.time_range.append((oldest_timestamp, LIBMEV_MIN_TIMESTAMP)) # 2022-01-01 00:00:00
        else:
            self.time_range.append((int(time.time()), LIBMEV_MIN_TIMESTAMP))

        self.start_time = self.time_range[0][0]

        # start worker threads
        for i in range(self.num_worker):
            if len(self.workers) == self.num_worker:
                break

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
                    self.bundle_tasks.update_done(task_id, len(bundles))
                    self.logger.debug(f'Task {task_id} - Inserted {len(bundles)} bundles')
                time.sleep(1)

                qsize = self.put_task()
                if qsize is None:
                    self.logger.info('All tasks are done - sleep 5 minutes')
                    time.sleep(300)
                    return self.run()

            except queue.Empty:
                self.check_threads_status()

    def get_time_range(self, start_time=None):
        if not self.time_range and start_time is None:
            return None

        start_time = None if start_time is None else start_time
        end_time = 0
        if start_time is None:
            time_range_end = self.time_range[0][1]
            if self.start_time < time_range_end:
                self.time_range.pop(0)
                self.start_time = self.time_range[0][0] if self.time_range else 0
                return self.get_time_range(start_time)

            start_time = self.start_time - (self.num_of_hours * 3600)
            end_time = self.start_time
            self.start_time = start_time
        else:
            end_time = start_time
            start_time = start_time - (self.num_of_hours * 3600)

        task_id = self.bundle_tasks.create(start_time, end_time)
        return task_id, start_time, end_time
