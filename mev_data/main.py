import logging
import time
import threading
import queue
from os import path, getenv
from dotenv import load_dotenv
from db.postgre import Postgres
from utils.helper import init_logger
from manage.bundle import BundleManager
from manage.tx import TxManager

load_dotenv()

class Main:
    def __init__(self):
        self.db = Postgres(getenv('DSN_POSTGRES'), 16)
        self.managers = [BundleManager(self.db), TxManager(self.db)]

    def prepare(self):
        self.db.create_table_bundles()
        self.db.create_table_txs()
        self.db.create_table_tasks()

    def run(self):
        self.prepare()
        for manager in self.managers:
            t = threading.Thread(target=manager.run)
            t.start()

        while True:
            time.sleep(3600)


if __name__ == '__main__':
    logger = logging.getLogger()
    path_config = path.join(path.dirname(__file__), 'config/log_config.yml')
    init_logger(path_config)
    Main().run()
