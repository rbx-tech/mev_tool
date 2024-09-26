import logging
import psycopg2
import psycopg2.extras
from psycopg2.pool import ThreadedConnectionPool


class Postgres:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, dsn, max_conn: int = 1):
        self.logger = logging.getLogger()
        try:
            self.pool = ThreadedConnectionPool(1, max_conn, dsn)
        except Exception as err:
            self.logger.error(f'Error connecting to database: {err}')
            raise err

    @classmethod
    def get_instance(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = cls(*args, **kwargs)
        return cls._instance

    def close(self):
        self.pool.closeall()

    def find_one(self, query):
        conn = self.pool.getconn()
        try:
            cur = conn.cursor()
            cur.execute(query)
            row = cur.fetchone()
            cur.close()
            return row
        finally:
            self.pool.putconn(conn)

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

    def execute(self, query, data=None):
        conn = self.pool.getconn()
        try:
            cur = conn.cursor()
            cur.execute(query, data)
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
