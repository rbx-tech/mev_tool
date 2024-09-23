import json
from db import Postgres
from utils.helper import chunk_list


class Bundles:
    def __init__(self):
        self.db = Postgres.get_instance()

    def create_table(self):
        query = """
            CREATE TABLE IF	NOT EXISTS bundles (
                bundle_hash VARCHAR (66) PRIMARY KEY,
                block_number INTEGER NOT NULL,
                "timestamp" INTEGER,
                tokens JSONB,
                searcher_gas_used INTEGER,
                bundle_gas_used INTEGER,
                searcher_eoa VARCHAR,
                searcher_contract VARCHAR(42),
                searcher_txs VARCHAR(66)[],
                burned_eth NUMERIC(30, 17),
                tipped_eth NUMERIC(30, 17),
                burned_usdc NUMERIC(30, 17),
                tipped_usdc NUMERIC(30, 17),
                profit_usdc NUMERIC(30, 17),
                profit_eth NUMERIC(30, 17),
                profit_margin NUMERIC(30, 17),
                builder_address VARCHAR(42),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        self.db.execute(query)

    def get_latest_bundle_timestamp(self):
        query = """
            SELECT timestamp FROM bundles ORDER BY "timestamp" DESC LIMIT 1
        """
        return self.db.query(query)

    def get_oldest_bundle_timestamp(self):
        query = """
            SELECT timestamp FROM bundles ORDER BY "timestamp" ASC LIMIT 1
        """
        return self.db.query(query)

    def get_paginated(self, page: int = 1, limit: int = 50):
        page = page if page > 0 else 1
        offset = (page - 1) * limit
        query = f"""
            SELECT searcher_txs
            FROM bundles 
            ORDER BY "timestamp" ASC
            LIMIT {limit} 
            OFFSET {offset}
        """

        return self.db.query(query)

    def batch_insert(self, bundles):
        batch = []

        for b in bundles:
            batch.append((
                b['bundle_hash'],
                b['block_number'],
                b['timestamp'],
                json.dumps(b['tokens']),
                b['searcher_gas_used'],
                b['bundle_gas_used'],
                b['searcher_eoa'],
                b['searcher_contract'],
                b['searcher_txs'],
                b['burned_eth'],
                b['tipped_eth'],
                b['burned_usdc'],
                b['tipped_usdc'],
                b['profit_usdc'],
                b['profit_eth'],
                b['profit_margin'],
                b['builder_address']
            ))

        query = """
            INSERT INTO bundles (
                bundle_hash, block_number, "timestamp", tokens, searcher_gas_used, bundle_gas_used, 
                searcher_eoa, searcher_contract, searcher_txs, burned_eth, tipped_eth, burned_usdc, 
                tipped_usdc, profit_usdc, profit_eth, profit_margin, builder_address
            ) VALUES %s
            ON CONFLICT (bundle_hash) DO NOTHING
        """

        chunks = chunk_list(batch, 1000)
        for c in chunks:
            self.db.batch_insert(query, c)
