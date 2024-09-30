import threading
import logging
import requests
from enum import Enum


class TaskStatus(Enum):
    SUCCESS = 1
    ERROR = 2
    DONE = 3


class TokenPriceWorker(threading.Thread):
    def __init__(self, task_queue, task_done_queue, *args, **kwargs):
        threading.Thread.__init__(self, *args, **kwargs)
        self.logger = logging.getLogger()
        self.task_queue = task_queue
        self.token = None
        self.task_done_queue = task_done_queue

    def run(self):
        self.logger.info(f'{self.name} started')
        while True:
            token = self.task_queue.get()
            if token is None:
                self.logger.info(f'{self.name} is done')
                break
            # try:
            self.logger.info(f'{self.name} processing {token["name"]}')
            self.token = token
            token_prices = self.get_prices_by_time_range()
            self.task_done_queue.put(self.format_token_prices(token_prices))
            # except Exception as e:
            #     self.logger.error(f'{self.name} error: {e}')
            #     self.task_queue.put(token)

    def format_token_prices(self, token_prices: list):
        return [
            (
                self.token['address'],
                self.token['name'],
                t['quote']['open'],
                t['quote']['close'],
                t['quote']['high'],
                t['quote']['low'],
                t['timeOpen'],
                t['timeClose'],
                t['timeHigh'],
                t['timeLow'],
                t['quote']['volume'],
                t['quote']['marketCap']
            )
            for t in token_prices
        ]

    def get_prices_by_time_range(self):
        time_start = self.token['time_range'][0]
        max_time_end = self.token['time_range'][1]
        result = []
        while True:
            time_end = time_start + 31536000 # 1 year
            if time_end > max_time_end:
                time_end = max_time_end
            token_prices = self.get_history_prices(self.token['id'], time_start, time_end)
            if not token_prices:
                break
            result.extend(token_prices)
            time_start = time_end
        return result

    def get_history_prices(self, id: int, time_start: int, time_end: int):
        url = f'https://api.coinmarketcap.com/data-api/v3.1/cryptocurrency/historical'
        params = {
            'id': id,
            'convertId': 2781,
            'timeStart': time_start,
            'timeEnd': time_end,
            'interval': '1d'
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()['data']['quotes']
