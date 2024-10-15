import multiprocessing
from time import sleep
from .mongo import MongoDb
from .runners.cycle_extractor import CycleExtractor


class RunnerManager:
    def start(self):
        mongo_db = MongoDb().connect()
        print('Connected to MongoDB!')

        cycle_extr_runner = None
        while (True):
            cycle_enable = mongo_db.get_info('enable_cycles_extractor', False)
            if not cycle_extr_runner:
                if cycle_enable:
                    print('Manager:', 'start cycles extractor')
                    runner = CycleExtractor()
                    cycle_extr_runner = multiprocessing.Process(target=runner.run)
                    cycle_extr_runner.start()
            elif not cycle_enable:
                if cycle_extr_runner.is_alive():
                    print('Manager:', 'cycles extractor was stopped!')
                    cycle_extr_runner.kill()

            sleep(1)
