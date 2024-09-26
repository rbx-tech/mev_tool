import logging
from db import Postgres
from utils import chunk_list, hex_to_int


class Txs:
    def __init__(self):
        self.db = Postgres.get_instance()
        self.logger = logging.getLogger()

    # CREATE TYPE tx_kind AS ENUM ('mev', 'victim');
    def create_table(self):
        query = """
            CREATE TABLE IF	NOT EXISTS txs (
                tx_hash VARCHAR (66) PRIMARY KEY,
                bundle_hash VARCHAR(66),
                block_hash VARCHAR(66),
                block_number INTEGER,
                "from" VARCHAR(42),
                "to" VARCHAR(42),
                "value" VARCHAR(64),
                gas INTEGER,
                gas_price BIGINT,
                max_fee_per_gas BIGINT,
                max_priority_fee_per_gas BIGINT,
                "input" TEXT,
                nonce INTEGER,
                transaction_index SMALLINT,
                "type" SMALLINT,
                kind tx_kind,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        self.db.execute(query)

    def get_txs_empty(self, limit: int = 50):
        query = f"""
            SELECT tx_hash 
            FROM txs 
            WHERE block_number = 0
            ORDER BY created_at ASC
            LIMIT {limit}
        """
        return self.db.query(query)

    def get_txs_decode_empty(self, to: str, limit: int = 50):
        query = f"""
            SELECT t.tx_hash, t."input"
            FROM txs t
            LEFT JOIN tx_inputs ti ON t.tx_hash = ti.tx_hash
            WHERE ti.tx_hash IS NULL AND t."to" = '{to}'
            ORDER BY t.created_at ASC
            LIMIT {limit}
        """
        return self.db.query(query)

    def batch_insert_txs(self, txs):
        query = """
                UPDATE txs AS t
                SET
                    block_hash = v.block_hash,
                    block_number = v.block_number,
                    "from" = v."from",
                    "to" = v."to",
                    "value" = v."value",
                    gas = v.gas,
                    gas_price = v.gas_price,
                    max_fee_per_gas = v.max_fee_per_gas,
                    max_priority_fee_per_gas = v.max_priority_fee_per_gas,
                    "input" = v."input",
                    nonce = v.nonce,
                    transaction_index = v.transaction_index,
                    "type" = v."type"
                FROM (VALUES %s) AS v(
                    tx_hash, block_hash, block_number, "from", "to", "value", gas, gas_price,
                    max_fee_per_gas, max_priority_fee_per_gas, "input", nonce, transaction_index, "type"
                )
                WHERE t.tx_hash = v.tx_hash
            """

        batch = [
            (
                tx['hash'],
                tx.get('blockHash', None),
                int(tx['blockNumber'], 16),
                tx.get('from', None),
                tx.get('to', None),
                hex_to_int(tx.get('value')),
                hex_to_int(tx.get('gas')),
                hex_to_int(tx.get('gasPrice')),
                hex_to_int(tx.get('maxFeePerGas')),
                hex_to_int(tx.get('maxPriorityFeePerGas')),
                tx.get('input', None),
                hex_to_int(tx.get('nonce')),
                hex_to_int(tx.get('transactionIndex')),
                hex_to_int(tx.get('type')),
            )
            for tx in txs
        ]

        self.logger.debug(f'Updating {len(batch)} txs')
        chunks = chunk_list(batch, 1000)
        for c in chunks:
            self.db.batch_insert(query, c)

    def update_kind(self, tx_hashes):
        query = """
            UPDATE txs
            SET kind = 'mev'
            WHERE tx_hash = ANY(%s)
        """

        self.db.execute(query, (tx_hashes,))

    def batch_insert_txs_empty(self, bundles):
        batch = []

        for b in bundles:
            for tx in b['txs']:
                batch.append((
                    tx,
                    b['bundle_hash'],
                    0
                ))

        query = """
            INSERT INTO txs (
                tx_hash, bundle_hash, block_number
            ) VALUES %s
            ON CONFLICT (tx_hash) DO NOTHING
        """

        chunks = chunk_list(batch, 1000)
        for c in chunks:
            self.db.batch_insert(query, c)
