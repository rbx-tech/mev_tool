import json
import sys
import os
from pymongo import UpdateOne

sys.path.append(os.getcwd())
from src.utils import read_from_file
from src.mongo import MongoDb


mongodb = MongoDb()
mongodb.connect()


def update_many_pools(updates):
    result = mongodb.pools.bulk_write(updates)
    print(
        f"Result inserted_count={result.inserted_count} upserted_count={result.upserted_count} "
        f"modified_count={result.modified_count}"
    )


def insert_uniswap_v3_pools():
    text = read_from_file("./tmp/pairs/uniswap_v3.json")
    pools = dict(json.loads(text))

    updates = []
    for addr in pools.keys():
        addr = str(addr).lower()
        pool = pools[addr]
        if len(updates) >= 10000:
            update_many_pools(updates)
            updates = []

        updates.append(
            UpdateOne(
                {"_id": addr},
                {
                    "$set": {
                        "_id": addr,
                        "fee": pool["fee"],
                        "tick_spacing": pool["tick_spacing"],
                        "tokens": [pool["token0"].lower(), pool["token1"].lower()],
                        "protocol": "UniSwapV3",
                        "dex": "Uni",
                    }
                },
                upsert=True,
            )
        )

    update_many_pools(updates)


def insert_uniswap_v2_pools(dex: str, protocol: str, path):
    text = read_from_file(path)
    pools = dict(json.loads(text))

    updates = []
    for addr in pools.keys():
        pool = pools[addr]
        addr = str(addr).lower()
        if len(updates) >= 10000:
            update_many_pools(updates)
            updates = []

        updates.append(
            UpdateOne(
                {"_id": addr},
                {
                    "$set": {
                        "_id": addr,
                        "tokens": [pool["token0"].lower(), pool["token1"].lower()],
                        "protocol": protocol,
                        "dex": dex,
                    }
                },
                upsert=True,
            )
        )

    update_many_pools(updates)


insert_uniswap_v2_pools("CroSwapV2", "CroSwapV2", "./tmp/pairs/croswap_v2.json")
insert_uniswap_v2_pools("PancakeSwapV2", "PancakeV2", "./tmp/pairs/pancakeswap_v2.json")
insert_uniswap_v2_pools("ShibaSwapV2", "UniswapV2", "./tmp/pairs/shibaswap_v2.json")
insert_uniswap_v2_pools("SushiSwapV2", "UniswapV2", "./tmp/pairs/sushiswap_v2.json")
insert_uniswap_v2_pools("Uni", "UniSwapV2", "./tmp/pairs/uniswap_v2.json")
insert_uniswap_v3_pools()
