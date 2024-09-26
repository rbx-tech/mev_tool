import { MongoClient } from "mongodb";
const uri = process.env['MONGO_URI'] || "mongodb://localhost:27018/eigenphy?authSource=admin";

class MongoDb {
  constructor() {
    this.mongoClient = new MongoClient(uri);
    this.db = null;
  }
  async connect() {
    const client = await this.mongoClient.connect();
    this.db = client.db('eigenphy');
  }

  get bundlesCol() {
    return this.db.collection('bundles');
  }

  get infoCol() {
    return this.db.collection('info');
  }

}

export const mongoDb = new MongoDb();
