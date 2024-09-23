from db import Postgres
from utils.helper import chunk_list


class TxFilters:
    def __init__(self):
        self.db = Postgres.get_instance()

    def create_table(self):
        query = """
            CREATE TABLE IF	NOT EXISTS tx_filters (
                tx_hash VARCHAR (66) PRIMARY KEY,
                is_v3 BOOLEAN DEFAULT FALSE,
                token_gt_2 BOOLEAN DEFAULT FALSE,
                addresses VARCHAR(42)[] DEFAULT NULL,
                address_names VARCHAR(100)[] DEFAULT NULL,
                tokens VARCHAR(42)[] DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        self.db.execute(query)

    def batch_insert(self, tx_filters):
        batch = []
        for tx_filter in tx_filters:
            batch.append((
                tx_filter['tx_hash'],
                tx_filter['is_v3'],
                tx_filter['token_gt_2'],
                tx_filter['addresses'],
                tx_filter['address_names'],
                tx_filter['tokens']
            ))

        query = """
            INSERT INTO tx_filters (
                tx_hash, is_v3, token_gt_2, addresses, address_names, tokens
            ) VALUES %s
            ON CONFLICT (tx_hash) DO NOTHING
        """
        chunks = chunk_list(batch, 1000)
        for c in chunks:
            self.db.batch_insert(query, c)
