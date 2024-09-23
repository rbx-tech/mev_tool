import logging
import threading
from os import path, getenv
from dotenv import load_dotenv
from utils.helper import init_logger
from db import Postgres
from models import Tasks, Txs, Bundles, BundleTasks, TxFilters, TxInputs
from manage import BundleManager, TxManager, TxFilterManager, DecodeInputManager

load_dotenv()


class Main:
    def __init__(self):
        self.db = Postgres(getenv('DSN_POSTGRES'), 16)
        self.threads = []
        self.managers = [
            # BundleManager(),
            # TxManager(),
            # TxFilterManager(),
            DecodeInputManager()
        ]

    def prepare(self):
        models = [TxFilters, Txs, Tasks, Bundles, BundleTasks, TxInputs]
        for model in models:
            model().create_table()

    def run(self):
        self.prepare()
        for manager in self.managers:
            t = threading.Thread(target=manager.run)
            t.start()
            self.threads.append(t)

        for t in self.threads:
            t.join()


if __name__ == '__main__':
    logger = logging.getLogger()
    path_config = path.join(path.dirname(__file__), 'config/log_config.yml')
    init_logger(path_config)
    Main().run()
