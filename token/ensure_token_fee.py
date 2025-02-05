import argparse
import asyncio
from pyrevm import EVM, BlockEnv
from web3 import Web3
from contract import Contract
from uniswap_smart_path import SmartPath
from eth_abi import encode
import time

MY_ADDR = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"  # vitalik.eth
BOT_ADDR = "0x66B8a48DD0A0F42A4f0cb8286ED796D41E664f07"  # vitalik.eth

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
    parse.add_argument("--rpc_url", default="http://192.168.1.58:8545")
    parse.add_argument("--file_path")
    return parse.parse_args()


def init_token() -> dict:
    global erc20token
    erc20token["0xa2b4c0af19cc16a6cfacce81f192b024d625817d"] = ERC20TokenFixedFee(200)  # 2%


def get_token(addr) -> ERC20Token:
    return erc20token.get(addr, ERC20Token())


def setup_contract(evm, file_path) -> dict:
    contracts = dict()
    token_contracts = dict()

    contracts["WETH"] = Contract(
        address="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        revm=evm,
        abi_file_path="./abi/weth.abi",
    )

    with open(file_path) as f:
        for line in f.readlines():
            token = line[0:42].rstrip()
            name = line[43:].rstrip()
            token_contracts[name] = Contract(address=token, revm=evm, abi_file_path="./abi/erc20.abi")

    contracts["UNISWAP_V2_ROUTER"] = Contract(
        "0x7a250d5630b4cf539739df2c5dacb4c659f2488d",
        revm=evm,
        abi_file_path="./abi/uniswapv2router.abi",
    )
    contracts["UNIVERSAL_ROUTER"] = Contract(
        "0x3fC91A3afd70395Cd496C647d5a6CC9d4B2b7FAD",
        revm=evm,
        abi_file_path="./abi/universal_router.abi",
    )
    contracts["UNISWAP_V2_FACTORY"] = Contract(
        "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f",
        revm=evm,
        abi_file_path="./abi/uniswapv2factory.abi",
    )

    return contracts, token_contracts


async def get_swap_path(rpc_url: str, amount_in: int, token_in: str, token_out: str):
    smart_path = await SmartPath.create(rpc_endpoint=rpc_url)
    return await smart_path.get_swap_in_path(
        amount_in,
        Web3.to_checksum_address(token_in),
        Web3.to_checksum_address(token_out),
    )


def execute_universal_swap(
    universal_router: Contract,
    path_info: dict,
    amount_in: int,
    recipient: str,
) -> tuple[int, int]:
    """Execute swap based on the path information returned by SmartPath"""

    if path_info["function"] == "V2_SWAP_EXACT_IN":
        # V2 swap command
        command = 0x08  # V2_SWAP_EXACT_IN command
        paths = path_info["path"]

        types = ["address", "uint256", "uint256", "address[]", "bool"]
        values = [
            recipient,
            amount_in,
            1,  # amount out min
            paths,
            False,  # payerIsUser
        ]
        inputs = encode(types, values)

    elif path_info["function"] == "V3_SWAP_EXACT_IN":
        # V3 swap command
        command = 0x00  # V3_SWAP_EXACT_IN command
        paths = path_info["path"]

        encoded_path = b""
        encoded_path += Web3.to_bytes(hexstr=paths[0])  # First token (20 bytes)

        # For each pair of (fee, token) after the first token
        for i in range(1, len(paths) - 1, 2):
            fee = paths[i]
            next_token = paths[i + 1]
            encoded_path += fee.to_bytes(3, "big")  # fee (3 bytes)
            encoded_path += Web3.to_bytes(hexstr=next_token)  # next token (20 bytes)

        types = ["address", "uint256", "uint256", "bytes", "bool"]
        values = [
            recipient,
            amount_in,
            100,  # amount out min
            encoded_path,
            False,  # payerIsUser
        ]
        inputs = encode(types, values)
    else:
        raise ValueError(f"Unsupported swap function: {path_info['function']}")

    # Execute the swap command
    commands = command.to_bytes(1, "big")  # Single byte command

    return universal_router.execute(commands, [inputs], caller=recipient)


async def check_token_fee(rpc_url: str, weth: Contract, token: Contract, contracts: dict[str, Contract]) -> CheckResult:
    check_result = CheckResult()
    current_balance = token.balanceOf(MY_ADDR)

    try:
        # Try direct V2 path first
        v2_router = contracts["UNISWAP_V2_ROUTER"]
        amount_in, amount_out = v2_router.swapExactTokensForTokens(
            1000000000,
            1,
            [weth.address, token.address],
            MY_ADDR,
            int(time.time()),
            caller=MY_ADDR,
        )
    except Exception:
        amount_in = 100000000
        # If direct path fails, use SmartPath to find best route
        paths = await get_swap_path(rpc_url, amount_in, weth.address, token.address)
        if not paths:
            check_result.has_v2_pair = False
            check_result.status = "NO_SWAP_PATH_FOUND"
            return check_result

        # Try paths in order they were returned
        universal_router = contracts["UNIVERSAL_ROUTER"]
        for path_info in paths:
            try:
                amount_in, amount_out = execute_universal_swap(universal_router, path_info, amount_in, MY_ADDR)
                print(f"Used {path_info['function']} path with weight {path_info['weight']}")
                break
            except Exception as e:
                print(f"ERROR {path_info['function']}: ", e)
                check_result.status = "EXEC_SWAP_ERROR"
                return check_result

    new_balance = token.balanceOf(MY_ADDR)

    actual_amount_out = new_balance - current_balance
    if actual_amount_out < amount_out:
        # TODO convert to rate and return it
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

    block = w3.eth.get_block(BLOCK_NUM, full_transactions=True)
    blockEnv = BlockEnv(number=block["number"], timestamp=block["timestamp"])
    evm = EVM(fork_url=args.rpc_url, fork_block=f"0x{block['parentHash'].hex()}", tracing=False)
    evm.set_block_env(blockEnv)
    contracts, token_contracts = setup_contract(evm, args.file_path)

    contracts["WETH"].deposit(value=10**19, caller=MY_ADDR)
    contracts["WETH"].approve(contracts["UNISWAP_V2_ROUTER"].address, 0x10000000000000000000, caller=MY_ADDR)
    contracts["WETH"].approve(contracts["UNIVERSAL_ROUTER"].address, 0x10000000000000000000, caller=MY_ADDR)

    for name, token in token_contracts.items():
        try:
            result = await check_token_fee(args.rpc_url, contracts["WETH"], token, contracts)
            print(
                f"Token {name} V2Pair: {result.has_v2_pair}, FeeSwap: {result.fee_swap}, fee_transfer: {result.fee_transfer}, status: {result.status}"
            )
        except Exception as ex:
            print("Token: ", name, " got error: ", ex)


if __name__ == "__main__":
    asyncio.run(main())
