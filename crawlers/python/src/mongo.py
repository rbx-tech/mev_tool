from pymongo import MongoClient
import os


class MongoDb:
    def __init__(self):
        self.db = None
        self.client = None

    def connect(self):
        mongo_uri = os.getenv('MONGO_URI', "mongodb://localhost:27018/mev?authSource=admin")
        self.client = MongoClient(mongo_uri)
        self.db = self.client.get_database()
        return self

    def close(self):
        self.client.close()

    @property
    def bundles(self):
        return self.db['bundles']

    @property
    def info(self):
        return self.db['info']

    @property
    def tokens(self):
        return self.db['tokens']

    @property
    def pools(self):
        return self.db['pools']

    @property
    def transactions(self):
        return self.db['transactions']

    @property
    def runners(self):
        return self.db['runners']

    def switch_db(self, db_name=None):
        self.db = self.client.get_database(db_name)

    def get_info(self, key, default_val=None):
        doc = self.info.find_one({'_id': key})
        if not doc:
            self.info.insert_one({'_id': key, 'value': default_val})
            return default_val
        return doc.get('value', default_val)

    def set_info(self, key, value):
        self.info.update_one({'_id': key}, {'$set': {'value': value}})
