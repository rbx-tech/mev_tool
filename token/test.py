import json
import os
from pyrevm import EVM, AccountInfo, BlockEnv, Env, TxEnv
from eth_hash.auto import keccak
import struct
import eth_abi
import eth_utils
from pyrevm_contract.contract import Contract
from web3 import Web3
from abi import ABIFunction, ContractABI
from contract import Contract

w3 = Web3(Web3.HTTPProvider("http://10.7.0.58:8545"))

mev_addr = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"  # vitalik.eth
address2 = "0xbBbBBBBbbBBBbbbBbbBbbbbBBbBbbbbBbBbbBBbB"

# use your own key during development to avoid rate limiting the CI job
fork_url = (
    os.getenv("FORK_URL")
    # or "https://mainnet.infura.io/v3/c60b0bb42f8a4c6481ecd229eddaca27"
    or "http://10.7.0.58:8545"
)

evm = EVM(fork_url=fork_url, fork_block="0x9e90df7c4005075bac2146c118abf4f00629b0c25ad7df17b48502012e5e1f94", tracing=False)

USDT_ADDR = "0xdAC17F958D2ee523a2206206994597C13D831ec7"
WETH_ADDR = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
UNISWAP_UNIVERSAL_ROUTER = "0x3fC91A3afd70395Cd496C647d5a6CC9D4B2b7FAD"

UNISWAP_V2_ROUTER = "0x7a250d5630b4cf539739df2c5dacb4c659f2488d"
SPX_TOKEN = "0xE0f63A424a4439cBE457D80E4f4b51aD25b2c56C"
JOE_TOKEN = "0x76e222b07C53D28b89b0bAc18602810Fc22B49A8"
NEIRO_TOKEN = "0x812ba41e071c7b7fa4ebcfb62df5f45f6fa853ee"



weth = Contract(
    address=WETH_ADDR,
    revm=evm,
    abi_file_path="./abi/weth.abi"
)
usdt = Contract(
    address=USDT_ADDR,
    revm=evm,
    abi_file_path="./abi/erc20.abi"
)

joe = Contract(
    address=JOE_TOKEN,
    revm=evm,
    abi_file_path="./abi/erc20.abi"
)

spx = Contract(
    address=SPX_TOKEN,
    revm=evm,
    abi_file_path="./abi/erc20.abi"
)

kobasu = Contract(
    address="0xCEb67a66c2c8a90980dA3A50A3F96c07525a26Cb",
    revm=evm,
    abi_file_path="./abi/erc20.abi"
)

catalorian = Contract(
    address="0x8baf5d75cae25c7df6d1e0d26c52d19ee848301a",
    revm=evm,
    abi_file_path="./abi/erc20.abi"
)


# 0x4e68ccd3e89f51c3074ca5072bbac773960dfa36 weth/usdt
uni_router = Contract(
    address=UNISWAP_UNIVERSAL_ROUTER,
    revm=evm,
    abi_file_path="./abi/universal_router.abi"
)

TRIA_TOKEN = Contract(
    address="0x9a594f5ed8d119b73525dfe23adbceca77fd828d",
    revm=evm,
    abi_file_path="./abi/erc20.abi"
)

TRIA_WETH_V2_ADDR = "0x2e193ef33357c50d92d8f27b1f9fc6c2bf278dff"
tria_weth_v2 = Contract(
    address=TRIA_WETH_V2_ADDR,
    revm=evm,
    abi_file_path="./abi/uniswapv2.abi"
)

uniswap_v2_router = Contract(
    UNISWAP_V2_ROUTER,
    revm=evm,
    abi_file_path="./abi/uniswapv2router.abi"
)

spx_weth_v3 = Contract(
    "0x7C706586679Af2BA6D1A9fC2DA9C6aF59883fdD3",
    revm=evm,
    abi_file_path="./abi/uniswapV3.abi"
)

cata_kobasu = Contract(
    address="0xcdb4cac89dfa55a00c9f7cbc1e2a6d635514d9ac",
    revm=evm,
    abi_file_path="./abi/uniswapv2.abi"
)

weth_kobasu = Contract(
    address="0x750874e6fb8dca30ce41d445e4baf8c76971f912",
    revm=evm,
    abi_file_path="./abi/uniswapv2.abi"
)


def test_v3_swap():
    block = w3.eth.get_block(block_identifier=20967700, full_transactions=True)
    print("Block hash", block["hash"].hex())
    blockEnv = BlockEnv(number=block["number"], timestamp=block["timestamp"])
    evm.set_block_env(blockEnv)
    balance = evm.get_balance(mev_addr)
    weth.deposit(value=10**19, caller=mev_addr)
    print("Current WETH: ", weth.balanceOf(mev_addr))

    transactions = block.transactions

    fake_tran_111()
    return

    for item in transactions:
        print("transaction hash", item["hash"].hex(), "index", item["transactionIndex"], "value", item["value"])
        tx = {
            "caller": item["from"],
            "to": item["to"],
            "value": item["value"],
            "calldata": item["input"],
        }
        try:
            result = evm.message_call(**tx)
            print("transaction hash", item["hash"].hex(), "Result", result.hex())
        except Exception as ex:
            print("tx_hash", item["hash"].hex(),"GOT ERROR: ", ex)


        if item["hash"].hex() == "0xe2d8f79c51405af334da54562d53de48c978e8c8dd13ce8264b69c246756005c":
            print("victim run ok")
            fake_tran_111()
            # custom ...
            return

def fake_trans_1():
    weth.transfer(TRIA_WETH_V2_ADDR, 249199998288265216, caller=mev_addr)
    tria_weth_v2.swap(389314968232110092976128, 0, mev_addr, b'', caller=mev_addr)
    balance = TRIA_TOKEN.balanceOf(mev_addr)
    print(balance)

def fake_trans_2():
    amount_in = 249199998288265216 #+ 126899997080813568
    # weth.transfer(TRIA_WETH_V2_ADDR, amount_in, caller=mev_addr)
    # Swap only use SPX
    # assert weth.approve(UNISWAP_V2_ROUTER, 0x10000000000000000000, caller=mev_addr) == True
    # result = uniswap_v2_router.swapExactTokensForTokens(amount_in, 1, [WETH_ADDR, TRIA_TOKEN.address, JOE_TOKEN, WETH_ADDR], mev_addr, 1734284800, caller=mev_addr)
    # print(result)


    assert weth.approve(UNISWAP_V2_ROUTER, 0x10000000000000000000, caller=mev_addr) == True
    result = uniswap_v2_router.swapExactTokensForTokens(amount_in, 1, [WETH_ADDR, TRIA_TOKEN.address, SPX_TOKEN], mev_addr, 1734284800, caller=mev_addr)
    print(result)
    spx.transfer(spx_weth_v3.address, result[-1], caller=mev_addr)
    MAX=0xFFFD8963EFD1FC6A506488495D951D5263988D25
    MIN=0x1000276a3
    print(result[-1])
    r1 = spx_weth_v3.swap(mev_addr, True, result[-1], MAX, b'', caller=mev_addr)

    print(r1)



# Swap 100000000.0000 <KABOSU> to 3771342238759005.0000 <CATALORIAN> (on SwapPool<CATALORIAN-KABOSU>)
# Swap 3771342238759005.0000 <CATALORIAN> to 162935502.5105 <Neiro> (on SwapPool<Neiro-CATALORIAN>)
# Swap 162935502.5105 <Neiro> to 55078627357.3550 <KABOSU> (on SwapPool<Neiro-KABOSU>)
# Sum: -6.311346845653537
# Amount out: 55078627357.35505
# Profit: 54978627357.35505 54978.62735735505 %


# DOGE2.0 0xF2ec4a773ef90c58d98ea734c0eBDB538519b988 => 
# Neiro 0x812Ba41e071C7b7fA4EBcFB62dF5F45f6fA853Ee
# KABOSU 0xCEb67a66c2c8a90980dA3A50A3F96c07525a26Cb
# COLON 0xD09Eb9099faC55eDCbF4965e0A866779ca365a0C
# n 0xc7bb03ddD9311fc0338bE013E7B523254092Fda9 => 
# D.O.G.E 0x46FDcDDfAD7C72A621E8298D231033Cc00e067c6
# WETH 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2
# TROLL 0xf8ebf4849F1Fa4FaF0DFF2106A173D3A6CB2eB3A
# DOGE2.0 0xF2ec4a773ef90c58d98ea734c0eBDB538519b988
#
# Swap 100000000.0000 <DOGE2.0> to 301.2227 <Neiro> (on SwapPool<Neiro-DOGE2.0 at 0x270250af8569D4ff712AaEbC2F5971A824249fA7>, reserves: 37300778732216385/12345975595155958293834)
# Swap 301.2227 <Neiro> to 101825.1426 <KABOSU> (on SwapPool<Neiro-KABOSU at 0x6A516271870A48F4F6c72044Ca64Ec9c69ac4efc>, reserves: 295012154985743721/100025823548037363904)
# Swap 101825.1426 <KABOSU> to 419.3238 <COLON> (on SwapPool<KABOSU-COLON at 0xb394243f6a2ca48659E76E327e24cfAB0Eb43b9B>, reserves: 482014096035609274/1990943882051664)
# Swap 419.3238 <COLON> to 3737667476876864.5000 <n> (on SwapPool<n-COLON at 0x39d0ec013B2996015581Ffb0277D969BC1B17d70>, reserves: 600212599573607680629205776/67135011834973)
# Swap 3737667476876864.5000 <n> to 209553450163838.2188 <D.O.G.E> (on SwapPool<D.O.G.E-n at 0xf99dE4F893c973a83696Bf8FCfD8c33612696085>, reserves: 89924187791477155569744899/1599107013959915921071661688)
# Swap 209553450163838.2188 <D.O.G.E> to 368080.3256 <WETH> (on SwapPool<D.O.G.E-WETH at 0xC98B2D550d8D123F8e6950E0758305E88511B037>, reserves: 13511508223539237872190544873/23804357302565487289)
# Swap 368080.3256 <WETH> to 40432468738796528.0000 <TROLL> (on SwapPool<WETH-TROLL at 0xB7426bFd2abF64428fA82A71b0D44B056FfCC286>, reserves: 342194358856882599722/37702082771415707118978446425933)
# Swap 40432468738796528.0000 <TROLL> to 155304408.8003 <DOGE2.0> (on SwapPool<DOGE2.0-TROLL at 0x29De87AD74A28a4e9Dc38749232e7e9ee3eE14b6>, reserves: 2033230638147375464877/527750044226925760527209840451)
# Sum: -0.44021693269037243
# Amount out: 155304408.80032885
# Profit: 55304408.80032885 (55.3044)%

DOGE2_TOKEN = Contract(
    address="0xF2ec4a773ef90c58d98ea734c0eBDB538519b988",
    revm=evm,
    abi_file_path="./abi/erc20.abi"
)

doge2_Neiro = Contract(
    address="0x270250af8569D4ff712AaEbC2F5971A824249fA7",
    revm=evm,
    abi_file_path="./abi/uniswapv2.abi"
)

def fake_tran_111():
    # weth.transfer("0xF2ec4a773ef90c58d98ea734c0eBDB538519b988", 249199998288265216, caller=mev_addr)
    # weth_kobasu.swap(100000000, 0, mev_addr, b'', caller=mev_addr)
    weth.approve(UNISWAP_V2_ROUTER, 0x10000000000000000000, caller=mev_addr)

    amount_in = 1000000001
    result = uniswap_v2_router.swapExactTokensForTokens(amount_in, 1, ["0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", "0xF2ec4a773ef90c58d98ea734c0eBDB538519b988"], mev_addr, 1734284800, caller=mev_addr)
    print(result)
    amount_in = 100000000
    print(doge2_Neiro.getReserves())

    result = uniswap_v2_router.swapExactTokensForTokens(amount_in, 1, ["0xF2ec4a773ef90c58d98ea734c0eBDB538519b988", "0x812Ba41e071C7b7fA4EBcFB62dF5F45f6fA853Ee"], mev_addr, 1734284800, caller=mev_addr)



if __name__ == "__main__":
  test_v3_swap()
