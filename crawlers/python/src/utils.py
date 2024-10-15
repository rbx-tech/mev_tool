def read_from_file(path: str, mode='r'):
    with open(path, mode) as f:
        return f.read()
