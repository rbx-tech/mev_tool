import { mongoDb } from "../mongo.js";
import { sleep } from "../utils/index.js";
import { Proxy4 } from "../utils/proxyv4.js";

export async function runCrawBuilder() {
  if (!mongoDb.db) {
    await mongoDb.connect();
  }
  const defaultHeaders = {
    'Host': 'eigenphi.io',
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
  };
  while (true) {
    const docs = await (mongoDb.transactionsCol.find({ type: "arbitrage", tag: "searcher", signalScanned: null}, { _id: 1, bundleId: 1 }).limit(100).toArray());
    if (!docs.length) {
      break;
    }

    const promises = [];
    for (const doc of docs) {
      const proxy = await Proxy4.genNew();
      promises.push(proxy.toClient().get(`https://eigenphi.io/api/v1/signalFinder?tx=${doc._id}`, { headers: defaultHeaders, timeout: 15000 })
        .then((r) => r.data)
        .catch((e) => null));
    }
    const results = await Promise.all(promises);
    console.log(`Got signal info of ${results.length} bundles`);
  }
  console.log('All txs of arbitrage were updated!');
}

runCrawBuilder()