import json
from db import Postgres


class TxInputs:
    def __init__(self):
        self.db = Postgres.get_instance()

    def create_table(self):
        query = """
            CREATE TABLE IF	NOT EXISTS tx_inputs (
                tx_hash VARCHAR (66) PRIMARY KEY,
                function_name VARCHAR(100) NOT NULL,
                args JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        self.db.execute(query)

    def batch_insert(self, tx_inputs):
        query = """
            INSERT INTO tx_inputs (tx_hash, function_name, args)
            VALUES %s
            ON CONFLICT (tx_hash) DO NOTHING
        """
        self.db.batch_insert(query, tx_inputs)
