import os
import re
import sys
import threading
import traceback
from time import sleep
from pymongo import UpdateOne

sys.path.append(os.getcwd())

from src.mongo import MongoDb


class State:
    threads = {}
    is_running = True


def target_run(mongodb: MongoDb, ids: dict):
    thread_id = threading.get_ident()
    print(thread_id, f"Start analyzing for {len(ids)} txs")
    txs: list[dict] = list(
        mongodb.transactions.find(
            {"_id": {"$in": ids}},
            {"_id": 1, "inputDecoded": 1, "contractName": 1},
        )
    )

    updates = []
    pairs_list = []
    for tx in txs:
        index = 0
        tx_hash = tx["_id"]
        is_v2 = "V2" in tx["contractName"]
        input_args = tx["inputDecoded"]["args"]
        func_name = tx["inputDecoded"]["func"]
        args_list = [[func_name, input_args]] if is_v2 else input_args["inputs"]["args"]

        for args in args_list:
            command = args[0]
            if "SWAP" not in command:
                continue
            path = args[1]["path"]
            path_str = list(filter(lambda x: isinstance(x, str), path))
            fees = list(filter(lambda x: not isinstance(x, str), path))
            token_path = list(map(lambda x: str(x).lower(), path_str))
            pairs = list(zip(token_path, token_path[1:]))
            protocol = "UniSwapV3" if "V3" in command else "UniSwapV2"
            for i, pair in enumerate(pairs):
                update = {
                    "input": {**args[1], "path": path},
                    "txHash": tx_hash,
                    "protocol": protocol,
                    "pair": pair,
                    "pool": None,
                    "router": tx.get("contractName"),
                    "_id": f"{tx_hash}_{index}",
                }
                if "V3" in protocol:
                    pairs_list.append((protocol, fees[i], list(pair)))
                    update["fee"] = fees[i]
                    update["input"]["command"] = command
                else:
                    pairs_list.append((protocol, 0, list(pair)))

                updates.append(update)
                index += 1

    if len(pairs_list) > 0:
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
    else:
        pools_results = []

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
        res = mongodb.swaps_analytics.bulk_write(bulk_updates)
        print(thread_id, f"Result modified={res.modified_count}, upserted={res.upserted_count}")
    else:
        print(thread_id, "No result found!")

    mongodb.transactions.update_many(
        {"_id": {"$in": ids}},
        {
            "$set": {"swapAnalyzed": True},
            "$unset": {"swapAnalyzing": 1},
        },
    )
    State.threads.pop(thread_id)


def main_loop():
    limit = mongodb.get_info("swap_analytics_limit", 50)
    runner_cnt = mongodb.get_info("swap_analytics_max_run", 25)
    take_cnt = abs(runner_cnt - len(State.threads.keys()))

    for _ in range(0, take_cnt):
        ids = list(
            mongodb.transactions.find(
                {
                    "swapAnalyzed": {"$ne": True},
                    "swapAnalyzing": {"$exists": 0},
                    "contractName": re.compile(r"(Universal|Uniswap)"),
                    "inputDecoded.args": {"$exists": 1},
                },
                {"_id": 1},
            ).limit(limit)
        )
        if len(ids) == 0:
            State.is_running = False
            break

        ids = list(map(lambda x: x["_id"], ids))
        mongodb.transactions.update_many({"_id": {"$in": ids}}, {"$set": {"swapAnalyzing": True}})
        t = threading.Thread(target=target_run, args=(mongodb, ids))
        t.start()
        State.threads[t.ident] = t


if __name__ == "__main__":
    mongodb = MongoDb()
    mongodb.connect()
    filter_map = {"swapAnalyzing": True}

    if mongodb.transactions.count_documents(filter_map) > 0:
        result = mongodb.transactions.update_many(filter_map, {"$unset": {"swapAnalyzing": 1}})
        print("Runner:", f"Reset {result.modified_count} pending run tx")

    while State.is_running:
        try:
            main_loop()
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(e)
            traceback.print_exc()
            sleep(1)
            continue
    print("Runner is stopped!")
