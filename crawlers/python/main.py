from src import RunnerManager
from src.utils import print_log


if __name__ == '__main__':
    try:
        manager = RunnerManager()
        manager.start()
    except KeyboardInterrupt:
        print_log('Force stopped!')
