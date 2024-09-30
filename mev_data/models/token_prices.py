import json
from db import Postgres


class TokenPrices:
    def __init__(self):
        self.db = Postgres.get_instance()

    def create_table(self):
        query = """
            CREATE TABLE IF	NOT EXISTS token_prices (
                address VARCHAR (42),
                symbol VARCHAR(100) NOT NULL,
                "open" NUMERIC(17, 10) NOT NULL,
                "close" NUMERIC(17, 10) NOT NULL,
                high NUMERIC(17, 10) NOT NULL,
                low NUMERIC(17, 10) NOT NULL,
                time_open TIMESTAMP NOT NULL,
                time_close TIMESTAMP NOT NULL,
                time_high TIMESTAMP NOT NULL,
                time_low TIMESTAMP NOT NULL,
                volume NUMERIC(14, 2) NOT NULL,
                market_cap NUMERIC(15, 2) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (address, time_open)
            )
        """
        self.db.execute(query)

    def batch_insert(self, token_prices: list):
        query = """
            INSERT INTO token_prices (address, symbol, "open", "close", "high", low, time_open, time_close, time_high, time_low, volume, market_cap)
            VALUES %s
            ON CONFLICT (address, time_open) DO NOTHING
        """
        self.db.batch_insert(query, token_prices)
