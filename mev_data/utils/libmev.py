import requests
import time
import logging
from requests.exceptions import HTTPError, RequestException
from utils.proxy import ProxyV6

class LibMev:
    def __init__(self):
        self.logger = logging.getLogger()
        self.proxy = ProxyV6()

    def request_get(self, url, retry: int = 10):
        for attempt in range(retry):
            try:
                res = requests.get(url, proxies=self.proxy.generate_proxies())
                res.raise_for_status()
                return res.json()
            except (HTTPError, RequestException) as err:
                # self.logger.debug(f'Attempt {attempt + 1} failed: {err}')
                if attempt < retry - 1:
                    time.sleep(attempt)
                else:
                    raise err

    def get_bundles(self, time_range: tuple, offset: int, limit: int = 50):
        url = (
            f'https://api.libmev.com/v1/bundles?'
            f'timestampRange={time_range[0]},{time_range[1]}&'
            f'filterByTags=naked_arb,backrun&'
            f'limit={limit}&offset={offset}&'
            f'orderByDesc=block_number'
        )
        return self.request_get(url)

    def get_detail(self, bundle_hash: str):
        url = f'https://api.libmev.com/v1/bundles/{bundle_hash}'
        return self.request_get(url)
