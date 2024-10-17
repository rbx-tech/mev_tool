from ast import arg
import datetime


def read_from_file(path: str, mode='r'):
    with open(path, mode) as f:
        return f.read()


def chunk_list(the_list, chunk_size):
    result_list = []
    while the_list:
        result_list.append(the_list[:chunk_size])
        the_list = the_list[chunk_size:]
    return result_list


def find_item(arr: list, func):
    for i, item in enumerate(arr):
        if func(i, item):
            return i, item
    return None


def is_valid_cycle(cycle: list[dict]):
    if len(cycle) <= 2:
        return False

    for i in range(0, len(cycle) - 1):
        s = cycle[i]
        d = cycle[i+1]
        if s['to'] != d['from']:
            return False
    first = cycle[0]
    last = cycle[-1]
    return first['from'] == last['to'] and first['token'] == last['token']


def print_log(*args):
    date = datetime.datetime.now()
    print(date.isoformat(), *args)
