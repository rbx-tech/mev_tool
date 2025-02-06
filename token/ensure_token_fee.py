import argparse
import asyncio
from pyrevm import EVM, BlockEnv
from web3 import Web3
from contract import Contract
from uniswap_smart_path import SmartPath

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
    router_type: str = "V2"
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
    contracts["UNISWAP_V3_ROUTER"] = Contract(
        "0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45",
        revm=evm,
        abi_file_path="./abi/uniswapv3router.abi",
    )
    contracts["UNISWAP_V2_FACTORY"] = Contract(
        "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f",
        revm=evm,
        abi_file_path="./abi/uniswapv2factory.abi",
    )

    return contracts, token_contracts


def execute_swap(router_type: str, router: Contract, path_info: dict, amount_in: int) -> tuple[int, int]:
    """Execute swap using either V2 or V3 router directly"""

    paths = path_info["path"]
    if isinstance(paths, (list, tuple)):
        path_addresses = paths
    else:
        path_addresses = [paths[0], paths[1]]

    # Calculate minimum output with 0.5% slippage tolerance
    amount_out_min = 1
    deadline = 2000000000  # Far future timestamp

    # print(f"Executing {router_type} swap with:")
    # print(f"Amount in: {amount_in}")
    # print(f"Min amount out: {amount_out_min}")
    # print(f"Path: {path_addresses}")

    if router_type == "V2":
        # Use swapExactTokensForTokens for V2 token->token swaps
        amount_out = router.swapExactTokensForTokens(
            amount_in,
            amount_out_min,
            path_addresses,
            MY_ADDR,  # recipient
            deadline,
            caller=MY_ADDR,
        )
        if len(amount_out) > 1:
            return amount_in, amount_out[1]
        else:
            return amount_in, amount_out[0]
    else:  # V3
        # Encode the path for V3
        encoded_path = b""
        encoded_path += Web3.to_bytes(hexstr=paths[0])  # First token (20 bytes)

        # For each pair of (fee, token) after the first token
        for i in range(1, len(paths) - 1, 2):
            fee = paths[i]
            next_token = paths[i + 1]
            encoded_path += fee.to_bytes(3, "big")  # fee (3 bytes)
            encoded_path += Web3.to_bytes(hexstr=next_token)  # next token (20 bytes)

        amount_out = router.exactInput(
            (
                encoded_path,  # path
                MY_ADDR,  # recipient
                amount_in,  # amountIn
                amount_out_min,  # amountOutMinimum
            ),
            caller=MY_ADDR,
        )
        return amount_in, amount_out


async def check_token_fee(
    smart_path: SmartPath,
    weth: Contract,
    token: Contract,
    contracts: dict[str, Contract],
) -> CheckResult:
    check_result = CheckResult()
    current_balance = token.balanceOf(MY_ADDR)

    amount_in = 10**14
    # If direct path fails, use SmartPath to find best route
    paths = await smart_path.get_swap_in_path(
        amount_in,
        Web3.to_checksum_address(weth.address),
        Web3.to_checksum_address(token.address),
    )
    if not paths:
        check_result.router_type = "None"
        check_result.status = "NO_SWAP_PATH_FOUND"
        return check_result

    # Try paths in order they were returned
    for path_info in paths:
        try:
            router_type = "V2" if path_info["function"] == "V2_SWAP_EXACT_IN" else "V3"
            check_result.router_type = router_type
            router = contracts["UNISWAP_V2_ROUTER"] if router_type == "V2" else contracts["UNISWAP_V3_ROUTER"]
            amount_in, amount_out = execute_swap(router_type, router, path_info, amount_in)
            break
        except Exception as e:
            print(f"\033[91mERROR {token.symbol()}, {path_info['function']}: {e}\033[0m")  # Red color
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

    # Deposit WETH
    contracts["WETH"].deposit(value=10**19, caller=MY_ADDR)
    MAX_UINT = 2**256 - 1
    contracts["WETH"].approve(contracts["UNISWAP_V2_ROUTER"].address, MAX_UINT, caller=MY_ADDR)
    contracts["WETH"].approve(contracts["UNISWAP_V3_ROUTER"].address, MAX_UINT, caller=MY_ADDR)

    # Check WETH balance
    weth_balance = contracts["WETH"].balanceOf(MY_ADDR)
    print(f"WETH balance before swap: {weth_balance}")

    # Print table header
    print(
        "\n{:<20} | {:<4} | {:>8} | {:>12} | {:<10}".format("Token", "Router Type", "FeeSwap", "FeeTransfer", "Status")
    )
    print("-" * 55)  # Separator line

    smart_path = await SmartPath.create(rpc_endpoint=args.rpc_url)
    try:
        for name, token in token_contracts.items():
            try:
                result = await check_token_fee(smart_path, contracts["WETH"], token, contracts)
                print(
                    "{:<20} | {:<4} | {:>8.2f} | {:>12.2f} | {:<10}".format(
                        name, result.router_type, result.fee_swap, result.fee_transfer, result.status
                    )
                )
            except Exception as ex:
                print(f"\033[91mERROR {name}: {ex}\033[0m")
    finally:
        # Clean up any remaining resources
        if hasattr(evm, "close"):
            await evm.close()


if __name__ == "__main__":
    asyncio.run(main())
