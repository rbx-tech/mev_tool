import json
import codecs
import logging
import logging.config
from os import path
from typing import Any
from ruamel.yaml import YAML

yaml = YAML(typ="safe", pure=True)


def read_file(file: str):
    with open(file) as f:
        return f.read()


def read__file_json(file_path: str):
    with open(file_path, 'r') as file:
        data = json.load(file)
        return data


def write_file_json(file_path: str, data):
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=2)


def get_yaml_config(path_yaml):
    with codecs.open(path_yaml, "r", encoding="utf-8") as fd:
        config = yaml.load(fd.read())
        file_name = config["handlers"]["file_handler"]["filename"]
        config["handlers"]["file_handler"]["filename"] = path.abspath(path.join(path.dirname(__file__), "../" + file_name))
        return config


def init_logger(path_file_config: str):
    log_config = get_yaml_config(path_file_config)
    logging.config.dictConfig(log_config)


def chunk_list(lst: list, chunk_size: int) -> list[list[Any]]:
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]
