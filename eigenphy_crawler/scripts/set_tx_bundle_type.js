import { mongoDb } from "../mongo.js";

async function run() {
  process.env['MONGO_URI'] = 'mongodb://10.7.0.50:27018/eigenphy?authSource=admin';
  await mongoDb.connect();
  let skips = 0;
  const limit = 1000;
  while (true) {
    const bundles = await mongoDb.bundlesCol.find({ types: 'arbitrage' }, { _id: 1 }).limit(limit).skip(skips).toArray();
    console.log(`Length=${bundles.length}, skip=${skips}, limit=${limit}`);
    if (bundles.length == 0) {
      break;
    }
    const bundleIds = bundles.map((it) => it._id);
    await mongoDb.transactionsCol.updateMany({bundleId: {$in: bundleIds}}, {$set: {type: 'arbitrage'}});
    skips += limit;
  }
  process.exit();
}


run();