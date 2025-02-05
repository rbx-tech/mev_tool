import unittest
import os
from contract import Contract
from pyrevm import EVM, BlockEnv
from web3 import Web3


FORK_URL = os.getenv("FORK_URL") or "http://192.168.1.58:8545"
BLOCK_NUM=20967700
ERC20_LIST = [
    ('DOGE2.0', '0xF2ec4a773ef90c58d98ea734c0eBDB538519b988'),
    ('Neiro', '0x812Ba41e071C7b7fA4EBcFB62dF5F45f6fA853Ee'),
    ('KABOSU', '0xCEb67a66c2c8a90980dA3A50A3F96c07525a26Cb'),
    ('COLON', '0xD09Eb9099faC55eDCbF4965e0A866779ca365a0C'),
    ('n', '0xc7bb03ddD9311fc0338bE013E7B523254092Fda9'),
    ('D.O.G.E', '0x46FDcDDfAD7C72A621E8298D231033Cc00e067c6'),
    ('TROLL', '0xf8ebf4849F1Fa4FaF0DFF2106A173D3A6CB2eB3A')
]

UNISWAP_V2_PAIRS = [
    ('Neiro-DOGE2.0', '0x270250af8569D4ff712AaEbC2F5971A824249fA7'),
    ('Neiro-KABOSU', '0x6A516271870A48F4F6c72044Ca64Ec9c69ac4efc')
]
MY_ADDR = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045" # vitalik.eth

class UniswapV2Test(unittest.TestCase):
    erc20_contracts: dict = dict()
    uniswap_v2_pairs: dict = dict()

    def init_contract(self):
        self.erc20_contracts["WETH"] = Contract(
            address="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            revm=self.evm,
            abi_file_path="./abi/weth.abi"
        )

        with open("data/token.txt") as f:
            for line in f.readlines():
                token = line[0: 42].rstrip()
                name = line[43:].rstrip()
                self.erc20_contracts[name] = Contract(
                    address=token,
                    revm=self.evm,
                    abi_file_path="./abi/erc20.abi"
                )
                ERC20_LIST.append((name, token))


        for name, addr in ERC20_LIST:
            self.erc20_contracts[name] = Contract(
                    address=addr,
                    revm=self.evm,
                    abi_file_path="./abi/erc20.abi"
                )

        for name, pair_addr in UNISWAP_V2_PAIRS:
            self.uniswap_v2_pairs[name] = Contract(
                address=pair_addr,
                revm=self.evm,
                abi_file_path="./abi/uniswapv2.abi"
            )

        self.uniswap_v2_router = Contract(
            "0x7a250d5630b4cf539739df2c5dacb4c659f2488d",
            revm=self.evm,
            abi_file_path="./abi/uniswapv2router.abi"
        )

        self.uniswap_v2_factory = Contract(
            "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f",
            revm=self.evm,
            abi_file_path="./abi/uniswapv2factory.abi"
        )


    def setUp(self) -> None:
        self.w3 = Web3(Web3.HTTPProvider(FORK_URL))
        block = self.w3.eth.get_block(block_identifier=BLOCK_NUM, full_transactions=True)
        self.evm = EVM(fork_url=FORK_URL, fork_block=block['parentHash'].hex(), tracing=False)
        self.init_contract()
        return super().setUp()


    def init_block(self, block_number):
        block = self.w3.eth.get_block(block_identifier=block_number, full_transactions=True)
        print("Block hash", block["hash"].hex())
        blockEnv = BlockEnv(number=block["number"], timestamp=block["timestamp"])
        self.evm.set_block_env(blockEnv)
        balance = self.evm.get_balance(MY_ADDR)
        self.erc20_contracts['WETH'].deposit(value=10**19, caller=MY_ADDR)
        print("Current WETH: ", self.erc20_contracts['WETH'].balanceOf(MY_ADDR))
        return block

    def test_transfer(self):

        block = self.init_block(BLOCK_NUM)
        self.erc20_contracts['WETH'].approve(self.uniswap_v2_router.address, 0x10000000000000000000, caller=MY_ADDR)
        # token transfer
        error = []
        result = []
        no_pair_with_eth = []
        receice_fee = []
        to_addr = "0xbBbBBBBbbBBBbbbBbbBbbbbBBbBbbbbBbBbbBBbB"
        block = self.init_block(BLOCK_NUM)
        self.erc20_contracts['WETH'].approve(self.uniswap_v2_router.address, 0x10000000000000000000, caller=MY_ADDR)
        for name, addr in ERC20_LIST:
            print("Transfer token Name: {}".format(name))
            old_balance = self.erc20_contracts[name].balanceOf(MY_ADDR)
            try:
                amount_in, amount_out = self.uniswap_v2_router.swapExactTokensForTokens(1000000000, 1, [self.erc20_contracts['WETH'].address, addr], MY_ADDR, 1734284800, caller=MY_ADDR)
            except:
                print("Swap WETH to {} error".format(name))
                no_pair_with_eth.append((name, addr))
                print("--" * 30)
            print("Swap {} amount {} to {} amount {}".format("WETH", amount_in, name, amount_out))
            print("Balance Token {} = {}".format(name, self.erc20_contracts[name].balanceOf(MY_ADDR)))
            new_balance = self.erc20_contracts[name].balanceOf(MY_ADDR)

            if new_balance - old_balance != amount_out:
                print("Token {} fee receice token".format(name))
                receice_fee.append((name, addr))
                amount_out = new_balance - old_balance
            if amount_out <= 0:
                continue
            try:
                self.erc20_contracts[name].transfer(to_addr, amount_out, caller=MY_ADDR)
                balance = self.erc20_contracts[name].balanceOf(to_addr)
                if balance != amount_out:
                    print("Token {} transfer with fee".format(name))
                    result.append((name, addr))
            except:
                error.append((name, addr))

            print("--" * 30)
        print("transfer fee: ", result)
        print("receive fee: ", receice_fee)
        print("No Pair with ETH: ", no_pair_with_eth)
        print("ERROR: ", result)

if __name__ == "__main__":
    unittest.main()