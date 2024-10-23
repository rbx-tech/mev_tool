import os
import sys

sys.path.append(os.getcwd())

from src import mongo

def main():
  mongodb = mongo.MongoDb()
  mongodb.connect()

  names = {
    "0x3fc91a3afd70395cd496c647d5a6cc9d4b2b7fad":	"UniversalRouter",
    "0xef1c6e67703c7bd7107eed8303fbe6ec2554bf6b":	"UniversalRouter2",
    "0x7a250d5630b4cf539739df2c5dacb4c659f2488d":	"UniswapV2Router02",
    "0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45":	"UniswapV3Router2",
    "0x888888888889758f76e7103c6cbf23abbf58f946":	"PendleRouterV4",
    "0x6131b5fae19ea4f9d964eac0408e4408b66337b5":	"KyberSwapMetaAggregationRouterv2",
    "0xc36442b4a4522e871399cd717abdd847ab11fe88":	"UniswapV3PositionsNFT",
    "0x03f7724180aa6b939894b5ca4314783b0b36b329":	"ShibaSwapRouter",
    "0xd9e1ce17f2641f24ae83637ab66a2cca9c378b9f":	"SushiSwapRouter",
    "0x1111111254eeb25477b68fb85ed929f73a960582":	"1inchV5",
    "0x1111111254fb6c44bac0bed2854e76f90643097d":	"1inchV4",
    "0x111111125421ca6dc452d289314280a0f8842a65":	"1inchV6",
    "0xdef1c0ded9bec7f1a1670819833240f027b25eff":	"0xExchangeProxy",
    "0x881d40237659c251811cec9c364ef91dc08d300c":	"MetamaskSwapRouter",
    "0x00000047bb99ea4d791bb749d970de71ee0b1a34":	"TransitSwapv5Router",
    "0x80a64c6d7f12c47b7c66c5b4e20e72bc1fcd5d9e":	"MaestroRouter2",
    "0x7d0ccaa3fac1e5a943c5168b6ced828691b46b36":	"OKXDexRouter",
    "0xeaaa41cb2a64b11fe761d41e747c032cdd60cace":	"EthervistaRouter",
    "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48":	"CircleUSDCToken",
    "0xe592427a0aece92de3edee1f18e0157c05861564":	"UniswapV3Router",
    "0x3c11f6265ddec22f4d049dde480615735f451646": "MimicSwapper",
    "0x00000000009726632680fb29d3f7a9734e3010e2": "RainbowRouter",
    "0xc49e4717fb9de97ddb4bfa5814372865249d3447": "ZeroExProxy",
    "0xead811d798020c635cf8dd4ddf31bdc5595b09f3": "EtherVistaRouter",
  }
  
  for k in names.keys():
    result = mongodb.transactions.update_many({'contractName': None, 'raw.to': k}, {
      '$set': {
        'contractName': names[k]
      }
    })
    print(f'Update Result: {result}')
if __name__ == '__main__':
  main()
