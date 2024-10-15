from src import RunnerManager


if __name__ == '__main__':
    try:
        manager = RunnerManager()
        manager.start()
    except KeyboardInterrupt:
        print('Force stopped!')
