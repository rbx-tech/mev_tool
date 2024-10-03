import { MongoClient } from "mongodb";
const uri = () => process.env['MONGO_URI'] || "mongodb://localhost:27018/eigenphy?authSource=admin";

class MongoDb {
  constructor() {
    this.db = null;
  }
  async connect() {
    this.mongoClient = new MongoClient(uri());
    const client = await this.mongoClient.connect();
    this.db = client.db('eigenphy');
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

}

export const mongoDb = new MongoDb();
