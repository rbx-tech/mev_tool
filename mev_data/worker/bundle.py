import threading
import time
import logging
from os import getenv
from utils.libmev import LibMev

NUMBER_OF_HOURS = int(getenv('NUMBER_OF_HOURS', '6'))


class BundleWorker(threading.Thread):
    def __init__(self, db, task_queue, task_done_queue, *args, **kwargs):
        threading.Thread.__init__(self, *args, **kwargs)
        self.db = db
        self.logger = logging.getLogger()
        self.lib_mev = LibMev()
        self.task_queue = task_queue
        self.task_done_queue = task_done_queue
        self.task_id = 0

    def run(self):
        self.logger.info(f'{self.name} started')
        while True:
            start_time = self.task_queue.get()
            if start_time <= 0:
                self.logger.info(f'{self.name} stopped')
                break
            try:
                bundles = self.get_bundles_past_hour(start_time)
                self.db.batch_insert_bundles(bundles)
                self.db.update_task_done(self.task_id, len(bundles))
                self.task_done_queue.put(True)
            except Exception as err:
                self.logger.error(f'{self.name} - {err}')
                self.task_queue.put(start_time)
                self.task_done_queue.put(False)

    def stop(self):
        self.db.close()
        self.task_done_queue.put(False)

    def get_bundles_past_hour(self, end_time):
        bundles = []
        offset = 0
        start_time = end_time - (NUMBER_OF_HOURS * 3600)

        self.task_id = self.db.create_task(start_time, end_time)
        self.logger.info(f'{self.name} - Fetching bundles from {start_time} to {end_time}')
        while True:
            res = self.lib_mev.get_bundles((start_time, end_time), offset)
            if not res['data']:
                break
            bundles.extend(res['data'])
            if res['count'] <= len(bundles):
                break
            offset += 50
            time.sleep(1)
        return bundles