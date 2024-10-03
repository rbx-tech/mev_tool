import { MongoClient } from "mongodb";

class MongoDb {
  constructor() {
    this.db = null;
  }

  async connect() {
    const mongoUri = process.env['MONGO_URI'] || "mongodb://localhost:27018/mev?authSource=admin";
    this.mongoClient = new MongoClient(mongoUri);
    const client = await this.mongoClient.connect();
    this.db = client.db('mev');
  }

  get bundlesCol() {
    return this.db.collection('bundles');
  }

  get infoCol() {
    return this.db.collection('info');
  }

  get tokensCol() {
    return this.db.collection('tokens');
  }

  get poolsCol() {
    return this.db.collection('pools');
  }

  get transactionsCol() {
    return this.db.collection('transactions');
  }

  get runners() {
    return this.db.collection('runners');
  }

  async getInfo(key, defaultVal = null)  {
    const doc = await this.infoCol.findOne({_id: key});
    if (!doc) {
      await this.infoCol.insertOne({_id: key, value: defaultVal});
      return defaultVal;
    }
    return doc.value || defaultVal;
  }

  async setInfo(key, value)  {
    await this.infoCol.updateOne({_id: key}, {$set: {value: value}});
  }
}

export const mongoDb = new MongoDb();
