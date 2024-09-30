from db import Postgres
from utils import chunk_list


class TxLogs:
    def __init__(self):
        self.db = Postgres.get_instance()

    def create_table(self):
        query = """
            CREATE TABLE IF	NOT EXISTS tx_logs (
                tx_hash VARCHAR (66) NOT NULL,
                address VARCHAR (42) NOT NULL,
                signature VARCHAR (10) NOT NULL,
                topics VARCHAR (66)[] NOT NULL,
                data TEXT NOT NULL,
                log_index SMALLINT NOT NULL,
                removed BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (tx_hash, log_index)
            )
        """
        self.db.execute(query)

    def batch_insert(self, tx_logs):
        query = """
            INSERT INTO tx_logs (
                tx_hash, address, signature, topics, data, log_index, removed 
            ) VALUES %s
            ON CONFLICT (tx_hash, log_index) DO NOTHING
        """
        chunks = chunk_list(tx_logs, 1000)
        for c in chunks:
            self.db.batch_insert(query, c)
