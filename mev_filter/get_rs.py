from utils.helper import read_file_json, write_file_json
from utils.rpc import RPC
import eth_abi
from hexbytes import HexBytes

RPC_URL = 'http://10.7.0.58:8545'
rpc = RPC(RPC_URL)


def get_rs(pair_address):
    data = '0x0902f1ac'
    result = rpc.eth_call(pair_address, data)
    return eth_abi.decode(['uint112', 'uint112', 'uint32'], HexBytes(result))


if __name__ == '__main__':
    shiba_pairs = read_file_json('pairs/shibaswap_v2.json')['pairs']
    for pair in shiba_pairs:
        print(f"Processing pair: {pair['address']}")
        pair_address = pair['address']
        rs = get_rs(pair_address)
        pair['token0']['reserve'] = str(rs[0])
        pair['token1']['reserve'] = str(rs[1])
        write_file_json('shibaswap_v2.json', {'pairs': shiba_pairs})
