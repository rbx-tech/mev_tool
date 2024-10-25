import os
import sys
import pg8000.dbapi
from pymongo import UpdateOne

sys.path.append(os.getcwd())

from src import mongo


def main():
    mongodb = mongo.MongoDb()
    mongodb.connect()
    postgre_cnn = pg8000.dbapi.connect(
        "postgres",
        password="Dev#2023",
        host="10.7.0.50",
        port=5432,
        database="mev_data",
    )
    postgre_cusor = postgre_cnn.cursor()

    limit = 500
    offset = mongodb.get_info("sync_pair_offset", 1000)
    while True:
        postgre_cusor.execute(f"SELECT * FROM labels WHERE kind='pair' OFFSET {offset} LIMIT {limit}")
        results = postgre_cusor.fetchall()
        if len(results) == 0:
            break

        updates = []
        for p in results:
            name = str(p[1])
            names = name.split(":")
            if len(names) > 1:
                protocol = names[0]
            else:
                protocol = ""
            updates.append(
                UpdateOne(
                    {"_id": p[0]},
                    {"$set": {"name": p[1], "protocol": protocol}},
                    upsert=True,
                )
            )

        result = mongodb.pools.bulk_write(updates)
        print(
            f"Update Result: offset={offset}, limit={limit}, userted_cnt={result.upserted_count}, updated={result.modified_count}"
        )
        offset += limit
        mongodb.set_info("sync_pair_offset", offset)


if __name__ == "__main__":
    main()
