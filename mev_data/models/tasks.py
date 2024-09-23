import json
from db import Postgres


class Tasks:
    def __init__(self):
        self.db = Postgres.get_instance()

    # CREATE TYPE task_kind AS ENUM ('bundle', 'tx', 'tx_filter');
    # ALTER TABLE tasks ADD CONSTRAINT unique_kind UNIQUE (kind);
    def create_table(self):
        query = """
            CREATE TABLE IF	NOT EXISTS tasks (
                id SERIAL PRIMARY KEY,
                kind task_kind NOT NULL,
                extra JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT unique_kind UNIQUE(kind)
            )
        """
        self.db.execute(query)

    def get_by_kind(self, kind: str):
        query = f"""
            SELECT * FROM tasks
            WHERE kind = '{kind}'
        """
        return self.db.find_one(query)

    def create(self, kind: str, extra: dict):
        query = f"""
            INSERT INTO tasks (kind, extra)
            VALUES ('{kind}', '{json.dumps(extra)}')
            ON CONFLICT (kind) DO UPDATE
            SET extra = '{json.dumps(extra)}'
        """
        self.db.execute(query)

    def update(self, kind: str, extra: dict):
        query = f"""
            UPDATE tasks
            SET extra = '{json.dumps(extra)}'
            WHERE kind = '{kind}'
        """
        self.db.execute(query)
