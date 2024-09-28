import threading
import time
import logging
from utils.libmev import LibMev


class BundleWorker(threading.Thread):
    def __init__(self, task_queue, task_done_queue, *args, **kwargs):
        threading.Thread.__init__(self, *args, **kwargs)
        self.logger = logging.getLogger()
        self.lib_mev = LibMev()
        self.task_queue = task_queue
        self.task_done_queue = task_done_queue

    def run(self):
        self.logger.info(f'{self.name} started')
        while True:
            task_id, start_time, end_time = self.task_queue.get()
            if start_time <= 0:
                self.logger.info(f'{self.name} stopped')
                break
            try:
                bundles = self.get_bundles_past_hour(start_time, end_time)
                self.task_done_queue.put((task_id, bundles))
            except Exception as err:
                self.logger.error(f'{self.name} - {err}')
                self.task_queue.put((task_id, start_time, end_time))
                self.task_done_queue.put(False)

    def stop(self):
        pass

    def get_bundles_past_hour(self, start_time, end_time):
        bundles = []
        offset = 0

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
