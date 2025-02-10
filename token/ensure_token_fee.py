import argparse
import asyncio
from pyrevm import EVM, BlockEnv
from web3 import Web3
from contract import Contract
from uniswap_smart_path import SmartPath
import csv
from datetime import datetime

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
    fee_type: str = ""


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

    ignore_tokens = ["0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2", "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"]
    with open(file_path) as f:
        for line in f.readlines():
            token = line[0:42].rstrip()
            name = line[43:].rstrip()
            if token.lower() in ignore_tokens:
                continue
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

    # Calculate minimum output with 0.5% slippage tolerance
    amount_out_min = 1
    deadline = 2000000000  # Far future timestamp

    if router_type == "V2":
        # For V2, check if pair exists and has liquidity
        factory = Contract(
            "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f",  # V2 factory
            revm=router.revm,
            abi_file_path="./abi/uniswapv2factory.abi",
        )

        pair_address = factory.getPair(paths[0], paths[1], caller=MY_ADDR)

        if pair_address == "0x0000000000000000000000000000000000000000":
            raise ValueError("NO_PAIR_FOUND")

        # Check pair reserves
        pair = Contract(pair_address, revm=router.revm, abi_file_path="./abi/uniswapv2.abi")
        reserves = pair.getReserves(caller=MY_ADDR)
        if reserves[0] == 0 or reserves[1] == 0:
            raise ValueError("NO_LIQUIDITY")

        # Use swapExactTokensForTokens for V2 token->token swaps
        amount_out = router.swapExactTokensForTokens(
            amount_in,
            amount_out_min,
            paths,
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

    # Test with different amounts to detect fee type
    test_amounts = [10**10, 10**11, 10**12]  # Test with two different amounts
    fees = []
    successful_path_info = None
    successful_router_type = None
    successful_router = None

    for amount_in in test_amounts:
        paths = await smart_path.get_swap_in_path(
            amount_in,
            Web3.to_checksum_address(weth.address),
            Web3.to_checksum_address(token.address),
        )
        if not paths:
            check_result.router_type = "None"
            check_result.status = "NO_SMART_PATH"
            return check_result

        # Try paths in order they were returned
        for path_info in paths:
            try:
                router_type = "V2" if path_info["function"] == "V2_SWAP_EXACT_IN" else "V3"
                check_result.router_type = router_type
                router = contracts["UNISWAP_V2_ROUTER"] if router_type == "V2" else contracts["UNISWAP_V3_ROUTER"]

                # Store successful path for subsequent swaps
                if successful_path_info is None:
                    successful_path_info = path_info
                    successful_router_type = router_type
                    successful_router = router

                # Use the same path that worked for first amount
                if successful_path_info:
                    path_info = successful_path_info
                    router_type = successful_router_type
                    router = successful_router

                initial_balance = token.balanceOf(MY_ADDR)
                amount_in_used, amount_out = execute_swap(router_type, router, path_info, amount_in)
                new_balance = token.balanceOf(MY_ADDR)
                actual_amount_out = new_balance - initial_balance

                if actual_amount_out < amount_out:
                    fee_percent = (amount_out - actual_amount_out) * 100 / amount_out
                    fees.append((amount_in_used, fee_percent))
                    print(f"Swap Fee for amount {amount_in_used}: {fee_percent}%")
                break
            except Exception as e:
                print(f"\033[91mERROR {token.symbol()}, {path_info['function']}: {e}\033[0m")  # Red color
                check_result.status = str(e)
                return check_result

    # Analyze fees to determine if fixed or dynamic
    if len(fees) >= 2:
        fee_variance = max(abs(fees[0][1] - fees[1][1]) for i in range(len(fees) - 1))
        is_fixed_fee = fee_variance == 0
        check_result.fee_type = "FIXED" if is_fixed_fee else "DYNAMIC"
        check_result.fee_swap = sum(fee[1] for fee in fees) / len(fees)
    else:
        check_result.fee_type = "UNKNOWN"
        check_result.fee_swap = fees[0][1] if fees else 0

    # Transfer the last swapped amount to check transfer fees
    if actual_amount_out > 0:
        token.transfer(BOT_ADDR, actual_amount_out, caller=MY_ADDR)
        bot_balance = token.balanceOf(BOT_ADDR)

        if bot_balance != actual_amount_out:
            print(f"Transfer Fee: {(actual_amount_out - bot_balance) * 100 / actual_amount_out}%")
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

    weth_balance = contracts["WETH"].balanceOf(MY_ADDR)
    print(f"WETH balance before swap: {weth_balance}")

    print(
        "\n{:<20} | {:<4} | {:>8} | {:>12} | {:<10} | {:<10}".format(
            "Token", "Router Type", "FeeSwap", "FeeTransfer", "Fee Type", "Status"
        )
    )
    print("-" * 70)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = f"data/token_fees_{timestamp}.csv"
    with open(csv_filename, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Token", "Router Type", "FeeSwap", "FeeTransfer", "Fee Type", "Status"])

        smart_path = await SmartPath.create(rpc_endpoint=args.rpc_url)
        try:
            for name, token in token_contracts.items():
                try:
                    result = await check_token_fee(smart_path, contracts["WETH"], token, contracts)
                    print(
                        "{:<20} | {:<4} | {:>8.2f} | {:>12.2f} | {:<10} | {:<10}".format(
                            name,
                            result.router_type,
                            result.fee_swap,
                            result.fee_transfer,
                            result.fee_type,
                            result.status,
                        )
                    )
                    writer.writerow(
                        [
                            name,
                            result.router_type,
                            f"{result.fee_swap:.2f}",
                            f"{result.fee_transfer:.2f}",
                            result.fee_type,
                            result.status,
                        ]
                    )
                except Exception as ex:
                    error_msg = f"ERROR {name}: {ex}"
                    print(f"\033[91m{error_msg}\033[0m")
                    writer.writerow([name, "ERROR", "", "", str(ex), BLOCK_NUM])
        finally:
            if hasattr(evm, "close"):
                await evm.close()

    print(f"\nResults saved to: {csv_filename}")


if __name__ == "__main__":
    asyncio.run(main())
