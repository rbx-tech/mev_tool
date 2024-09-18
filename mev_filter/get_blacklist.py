import eth_abi
from hexbytes import HexBytes
from utils.rpc import RPC
from utils.helper import write_file_json

RPC_URL = 'http://10.7.0.58:8545'
FACTORY_ADDRESS = '0xcBAE5C3f8259181EB7E2309BC4c72fDF02dD56D8'
NAME = 'NineInch'
MODE = 1

rpc = RPC(RPC_URL)


def get_blacklist():
    four_bytes_pool_length = '0x574f2ba3'
    four_bytes_get_pool = '0x1e3dd18b'
    if MODE == 2:
        four_bytes_pool_length = '0x956aae3a'
        four_bytes_get_pool = '0x3a1d5d8e'
    if MODE == 3:
        four_bytes_pool_length = '0xefde4e64'
        four_bytes_get_pool = '0x41d1de97'

    res = rpc.eth_call(FACTORY_ADDRESS, four_bytes_pool_length)
    pool_length = eth_abi.decode(['uint256'], HexBytes(res))[0]
    print("pool length ", pool_length)
    result = {}
    for i in range(pool_length):
        print("Processing pool index: ", i)
        res = rpc.eth_call(FACTORY_ADDRESS, four_bytes_get_pool + eth_abi.encode(['uint256'], [i]).hex())
        pool_address = eth_abi.decode(['address'], HexBytes(res))[0]
        result[pool_address] = NAME
        write_file_json(f'{FACTORY_ADDRESS}.json', result)


if __name__ == '__main__':
    get_blacklist()