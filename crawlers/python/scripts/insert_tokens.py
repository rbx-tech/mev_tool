import json
import sys
import os
from pymongo import UpdateOne

sys.path.append(os.getcwd())
from src.utils import read_from_file
from src.mongo import MongoDb


mongodb = MongoDb()
mongodb.connect()


def update_many_tokens(updates):
    result = mongodb.tokens.bulk_write(updates)
    print(
        f"Result inserted_count={result.inserted_count} upserted_count={result.upserted_count} "
        f"modified_count={result.modified_count}"
    )


def insert_uniswap_v2_pools():
    text = read_from_file("./tmp/tokens/erc20_tokens.json")
    pools = dict(json.loads(text))

    updates = []
    for addr in list(pools.keys()):
        token = pools[addr]
        try:
            addr = str(addr).lower()
            if len(updates) >= 10000:
                update_many_tokens(updates)
                updates = []

            dec = token["decimals"]
            if dec > 100:
                print(token)
                continue

            updates.append(
                UpdateOne(
                    {"_id": addr},
                    {
                        "$set": {
                            "_id": addr,
                            "type": "erc20",
                            "name": token["name"],
                            "symbol": token["symbol"],
                            "decimals": token["decimals"],
                        }
                    },
                    upsert=True,
                )
            )
        except Exception as e:
            print("Error", e)
            print(token)

    update_many_tokens(updates)


insert_uniswap_v2_pools()
