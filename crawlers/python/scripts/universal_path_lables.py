import os
import re
import sys
import threading
import traceback
from time import sleep
from pymongo import UpdateOne

sys.path.append(os.getcwd())

from src.mongo import MongoDb


class Config:
    is_running = True


def target_run(mongodb: MongoDb, offset, limit):
    print(f"Start threading offset={offset}")

    txs = list(
        mongodb.transactions.find(
            {
                "contractName": re.compile(r"UniversalRouter"),
                "inputDecoded.func": "execute",
            },
            {"_id": 1, "inputDecoded": 1},
        )
        .limit(limit)
        .skip(offset)
    )
    if len(txs) == 0:
        print("All Universal tx were finished")
        Config.is_running = False
        return

    updates = []
    pairs_list = []
    for tx in txs:
        tx_hash = tx["_id"]
        index = 0
        for args in tx["inputDecoded"]["args"]["inputs"]:
            command = args[0]
            if "SWAP" not in command:
                continue
            path = args[1]["path"]
            path_str = list(filter(lambda x: isinstance(x, str), path))
            fees = list(filter(lambda x: not isinstance(x, str), path))
            token_path = list(map(lambda x: str(x).lower(), path_str))
            pairs = list(zip(token_path, token_path[1:]))
            protocol = "UniSwapV2" if "V2" in command else "UniSwapV3"
            for i, pair in enumerate(pairs):
                update = {
                    "input": {
                        "command": command,
                        **args[1],
                        "path": path,
                    },
                    "protocol": protocol,
                    "pair": pair,
                    "pool": None,
                    "_id": f"{tx_hash}_{index}",
                }
                if "V3" in protocol:
                    pairs_list.append((protocol, fees[i], list(pair)))
                    update["fee"] = fees[i]
                else:
                    pairs_list.append((protocol, 0, list(pair)))

                updates.append(update)
                index += 1

    pools_results = list(
        mongodb.pools.find(
            {
                "$or": [
                    {
                        "protocol": protocol,
                        **({"fee": fee} if "V3" in protocol else {}),
                        "$or": [
                            {"tokens": pair},
                            {"tokens": [pair[1], pair[0]]},
                        ],
                    }
                    for protocol, fee, pair in pairs_list
                ]
            }
        )
    )
    bulk_updates = []
    for update in updates:
        pair = update["pair"]
        del update["pair"]
        update["tokens"] = pair
        pools = list(
            filter(
                lambda x: x["protocol"] == update["protocol"] and pair[0] in x["tokens"] and pair[1] in x["tokens"],
                pools_results,
            )
        )
        if len(pools) > 0:
            update["pool"] = pools[0]

        bulk_updates.append(UpdateOne({"_id": update["_id"]}, {"$set": update}, upsert=True))

    if len(bulk_updates) > 0:
        res = mongodb.universal_analytics.bulk_write(bulk_updates)
        print(f"Result offset={offset} limit={limit}: modified={res.modified_count}, upserted={res.upserted_count}")
    else:
        print(f"No result found offset={offset} limit={limit}!")


def run():
    mongodb = MongoDb()
    mongodb.connect()

    offset = mongodb.get_info("universal_analytics_offset", 0)
    limit = 100

    threads: list[threading.Thread] = []

    while Config.is_running:
        runner_cnt = mongodb.get_info("universal_analytics_max_run", 25)
        for _ in range(0, runner_cnt):
            t = threading.Thread(target=target_run, args=(mongodb, offset, limit))
            t.start()
            threads.append(t)
            offset += limit

        for t in threads:
            t.join()

        if Config.is_running:
            mongodb.set_info("universal_analytics_offset", offset)


if __name__ == "__main__":
    while True:
        if not Config.is_running:
            break
        try:
            run()
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(e)
            traceback.print_exc()
            sleep(1)
            continue
    print("Runner is stopped!")
