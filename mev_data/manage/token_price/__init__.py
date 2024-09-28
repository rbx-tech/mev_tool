import queue
import logging
from os import getenv
from utils import read_file_json, write_file_json
from .worker import TokenPriceWorker, TaskStatus
from models import TokenPrices


class TokenPriceManager:
    def __init__(self):
        self.logger = logging.getLogger()
        self.kind = 'token_price'
        self.token_prices = TokenPrices()
        self.tokens = []
        self.workers = []
        self.is_stop = False
        self.count_insert = 0
        self.num_worker = int(getenv('NUM_WORKER_TOKEN_PRICE', 5))
        self.task_queue = queue.Queue()
        self.task_done_queue = queue.Queue()

    def save_to_file(self):
        if self.count_insert >= self.num_worker * 2:
            write_file_json('data.json', self.tokens)
            self.count_insert = 0
        else:
            self.count_insert += 1

    def put_task_queue(self):
        if len(self.tokens) <= self.num_worker:
            return self.task_queue.put(None)
        self.task_queue.put(self.tokens[self.num_worker])

    def check_completed(self):
        self.is_stop = all(not worker.is_alive() for worker in self.workers)

    def prepare(self):
        # load coinmarketcap.json
        self.tokens = read_file_json('manage/token_price/coinmarketcap.json')
        self.num_worker = min(self.num_worker, len(self.tokens))
        for i in range(self.num_worker):
            self.task_queue.put(self.tokens[i])

    def run(self):
        self.prepare()
        self.logger.info(f'{self.__class__.__name__} is running')

        for i in range(self.num_worker):
            worker = TokenPriceWorker(
                task_queue=self.task_queue,
                task_done_queue=self.task_done_queue,
                name=f'{self.kind}-{i}')
            worker.start()
            self.workers.append(worker)

        while self.is_stop is False:
            try:
                data = self.task_done_queue.get(timeout=180)
                self.batch_insert(data)
                self.put_task_queue()
            except queue.Empty:
                self.check_completed()
                continue

    def delete_token(self, address: str):
        for token in self.tokens:
            if token['address'] == address:
                self.tokens.remove(token)
                break

    def batch_insert(self, data: list):
        if not data:
            return
        self.delete_token(data[0][0])
        self.token_prices.batch_insert(data)
        self.save_to_file()


