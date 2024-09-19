import json
import psycopg2
import psycopg2.extras
from psycopg2.pool import ThreadedConnectionPool
import logging
from utils.helper import chunk_list


class Postgres:
    def __init__(self, dsn, max_conn: int = 1):
        self.logger = logging.getLogger()
        try:
            self.pool = ThreadedConnectionPool(1, max_conn, dsn)
        except Exception as err:
            self.logger.error(f'Error connecting to database: {err}')
            raise err

    def close(self):
        self.pool.closeall()

    def create_table_bundles(self):
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
        self.execute(query)

    def create_table_txs(self):
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        self.execute(query)

    def create_table_tasks(self):
        query = """
            CREATE TABLE IF	NOT EXISTS tasks (
                id SERIAL PRIMARY KEY,
                start_time INTEGER NOT NULL,
                end_time INTEGER NOT NULL,
                is_done BOOLEAN DEFAULT FALSE,
                count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        self.execute(query)

    def get_latest_bundle_timestamp(self):
        query = """
            SELECT timestamp FROM bundles ORDER BY "timestamp" DESC LIMIT 1
        """
        return self.query(query)

    def get_oldest_bundle_timestamp(self):
        query = """
            SELECT timestamp FROM bundles ORDER BY "timestamp" ASC LIMIT 1
        """
        return self.query(query)

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
                tx['blockHash'],
                int(tx['blockNumber'], 16),
                tx['from'],
                tx['to'],
                int(tx['value'], 16),
                int(tx['gas'], 16),
                int(tx['gasPrice'], 16),
                int(tx.get('maxFeePerGas', '0x0'), 16),
                int(tx.get('maxPriorityFeePerGas', '0x0'), 16),
                tx['input'],
                int(tx['nonce'], 16),
                int(tx['transactionIndex'], 16),
                int(tx['type'], 16)
            )
            for tx in txs
        ]

        self.logger.debug(f'Updating {len(batch)} txs')
        chunks = chunk_list(batch, 1000)
        for c in chunks:
            self.batch_insert(query, c)

    def batch_insert_txs_empty(self, bundles):
        batch = []

        for b in bundles:
            for tx in b['txs']:
                batch.append((
                    tx,
                    b['bundle_hash']
                ))

        query = """
            INSERT INTO txs (
                tx_hash, bundle_hash
            ) VALUES %s
            ON CONFLICT (tx_hash) DO NOTHING
        """

        self.logger.debug(f'Inserting {len(batch)} txs')
        chunks = chunk_list(batch, 1000)
        for c in chunks:
            self.batch_insert(query, c)

    def batch_insert_bundles(self, bundles):
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

        self.logger.debug(f'Inserting {len(batch)} bundles')
        chunks = chunk_list(batch, 1000)
        for c in chunks:
            self.batch_insert(query, c)

        self.batch_insert_txs_empty(bundles)

    def get_task(self, start_time, end_time):
        query = f"""
            SELECT id FROM tasks WHERE start_time = {start_time} AND end_time = {end_time}
        """
        return self.query(query)

    def create_task(self, start_time, end_time):
        task = self.get_task(start_time, end_time)
        if task:
            return task[0][0]
        else:
            query = f"""
                INSERT INTO tasks (start_time, end_time)
                VALUES ({start_time}, {end_time})
                RETURNING id
            """
            return self.query(query)[0][0]

    def update_task_done(self, task_id, count: int):
        query = f"""
            UPDATE tasks SET is_done = TRUE, count = {count} WHERE id = {task_id}
        """
        self.execute(query)

    def get_tasks_not_done(self):
        query = """
            SELECT end_time FROM tasks WHERE is_done = FALSE
        """
        return self.query(query)

    def get_txs_empty(self, limit: int = 50):
        query = f"""
            SELECT tx_hash 
            FROM txs 
            WHERE block_hash IS NULL 
            ORDER BY created_at ASC
            LIMIT {limit}
        """
        return self.query(query)

    def query(self, query):
        conn = self.pool.getconn()
        try:
            cur = conn.cursor()
            cur.execute(query)
            conn.commit()
            rows = cur.fetchall()
            cur.close()
            return rows
        finally:
            self.pool.putconn(conn)

    def execute(self, query):
        conn = self.pool.getconn()
        try:
            cur = conn.cursor()
            cur.execute(query)
            conn.commit()
            cur.close()
        finally:
            self.pool.putconn(conn)

    def batch_insert(self, query, data):
        conn = self.pool.getconn()
        try:
            cur = conn.cursor()
            psycopg2.extras.execute_values(cur, query, data)
            conn.commit()
            cur.close()
        finally:
            self.pool.putconn(conn)