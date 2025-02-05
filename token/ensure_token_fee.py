import argparse
import asyncio
from pyrevm import EVM, BlockEnv
from web3 import Web3
from contract import Contract
from uniswap_smart_path import SmartPath

MY_ADDR = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045" # vitalik.eth
BOT_ADDR = "0x66B8a48DD0A0F42A4f0cb8286ED796D41E664f07" # vitalik.eth

erc20token = dict()

class ERC20Token:
    # No fee
    def transfer(self, amount: int) -> int:
        return amount

class ERC20TokenFixedFee(ERC20Token):
    fee_rate: int

    def __init__(self, fee_rate: int):
        self.fee_rate = fee_rate

    def transfer(self, amount: int) -> int:
        return amount - int(amount * self.fee_rate / 10000)


class CheckResult:
    has_v2_pair: bool = True
    fee_swap: int = 0
    fee_transfer: int = 0
    fee_recieve: int = 0
    status: str = ""

def get_args() -> argparse.Namespace:
    parse = argparse.ArgumentParser()
    parse.add_argument('--rpc_url', default='http://192.168.1.58:8545')
    parse.add_argument('--file_path')
    return parse.parse_args()


def init_token() -> dict:
    global erc20token
    erc20token['0xa2b4c0af19cc16a6cfacce81f192b024d625817d'] = ERC20TokenFixedFee(200) # 2%

def get_token(addr) -> ERC20Token:
    return erc20token.get(addr, ERC20Token())

def setup_contract(evm, file_path) -> dict:
    contracts = dict()
    token_contracts = dict()

    contracts["WETH"] = Contract(
        address="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        revm=evm,
        abi_file_path="./abi/weth.abi"
    )

    with open(file_path) as f:
        for line in f.readlines():
            token = line[0: 42].rstrip()
            name = line[43:].rstrip()
            token_contracts[name] = Contract(
                address=token,
                revm=evm,
                abi_file_path="./abi/erc20.abi"
            )

    contracts["UNISWAP_V2_ROUTER"] = Contract(
        "0x7a250d5630b4cf539739df2c5dacb4c659f2488d",
        revm=evm,
        abi_file_path="./abi/uniswapv2router.abi"
    )
    contracts["UNISWAP_V2_FACTORY"] = Contract(
        "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f",
        revm=evm,
        abi_file_path="./abi/uniswapv2factory.abi"
    )

    return contracts, token_contracts

def check_token_fee(weth: Contract, token: Contract, router: Contract) -> CheckResult:
    check_result = CheckResult()
    current_balance = token.balanceOf(MY_ADDR)
    try:
        # WETH to token v2 protocol only
        amount_in, amount_out = router.swapExactTokensForTokens(1000000000, 1, [weth.address, token.address], MY_ADDR, 1734284800, caller=MY_ADDR)
    except:
        # Todo impl this
        # Use SmartPath to find path from token to other token
        # smart_path = await SmartPath.create(rpc_endpoint=args.rpc_url)
        # path = await smart_path.get_swap_in_path(10**16, "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", Web3.to_checksum_address("0xd084944d3c05cd115c09d072b9f44ba3e0e45921"))
        # print(path)
        check_result.has_v2_pair = False
        return check_result

    new_balance = token.balanceOf(MY_ADDR)

    actual_amount_out = new_balance - current_balance
    if actual_amount_out < amount_out:
        #TODO convert to rate and return it
        check_result.fee_swap = (amount_out - actual_amount_out) * 100 / amount_out

    token.transfer(BOT_ADDR, actual_amount_out, caller=MY_ADDR)

    bot_balance = token.balanceOf(BOT_ADDR)

    if bot_balance != actual_amount_out:
        check_result.fee_transfer = (actual_amount_out - bot_balance) * 100 / actual_amount_out

    expected_after_transfer = get_token(token.address).transfer(actual_amount_out)

    check_result.status = "WRONG_FEE" if expected_after_transfer != bot_balance else "OK"

    return check_result



async def main():
    args = get_args()
    BLOCK_NUM = 21070769
    w3 = Web3(Web3.HTTPProvider(args.rpc_url))

    block = w3.eth.get_block(block_identifier=BLOCK_NUM, full_transactions=True)
    blockEnv = BlockEnv(number=block["number"], timestamp=block["timestamp"])
    evm = EVM(fork_url=args.rpc_url, fork_block=block['parentHash'].hex(), tracing=False)
    evm.set_block_env(blockEnv)
    contracts, token_contracts = setup_contract(evm, args.file_path)

    contracts['WETH'].deposit(value=10**19, caller=MY_ADDR)
    contracts['WETH'].approve(contracts["UNISWAP_V2_ROUTER"].address, 0x10000000000000000000, caller=MY_ADDR)

    for name, token in token_contracts.items():
        try:
            result = check_token_fee(contracts['WETH'], token, contracts["UNISWAP_V2_ROUTER"])
            print("Token {} V2Pair: {}, FeeSwap: {}, fee_transfer: {}, status: {}".format(name, result.has_v2_pair, result.fee_swap, result.fee_transfer, result.status))
        except Exception as ex:
            print("Token: ",name, " got error: ", ex)


if __name__ == "__main__":
    asyncio.run(main())
