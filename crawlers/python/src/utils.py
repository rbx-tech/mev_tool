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
