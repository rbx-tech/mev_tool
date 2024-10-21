import multiprocessing
from time import sleep
from src.utils import print_log
from .mongo import MongoDb
from .runners.cycle_extractor import CycleExtractor


class RunnerManager:
    def start(self):
        mongo_db = MongoDb().connect()
        print_log('Connected to MongoDB!')

        cycle_extr_runner = None
        while (True):
            cycle_enable = mongo_db.get_info('cycles_extractor_enable', False)
            if not cycle_extr_runner:
                if cycle_enable:
                    print_log('Manager:', 'start cycles extractor')
                    runner = CycleExtractor()
                    cycle_extr_runner = multiprocessing.Process(target=runner.run)
                    cycle_extr_runner.start()
            elif not cycle_enable:
                if cycle_extr_runner.is_alive():
                    print_log('Manager:', 'cycles extractor was stopped!')
                    cycle_extr_runner.kill()

            sleep(1)
