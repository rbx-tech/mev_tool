import { mongoDb } from "../../mongo.js";
import { sleep } from "../../utils/index.js";
import { Proxy4 } from "../../utils/proxy4.js";

export async function runCrawlSignals() {
  const defaultHeaders = {
    'Host': 'eigenphi.io',
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
  };
  while (true) {
    const txs = await (mongoDb.transactionsCol.find(
      { "eigenphy.type": "arbitrage", "eigenphy.tag": "searcher", "eigenphy.signalScanned": null },
      { _id: 1, bundleId: 1 }
    ).limit(100).toArray());
    
    if (!txs.length) {
      break;
    }

    const promises = [];
    for (const tx of txs) {
      const proxy = await Proxy4.genNew();
      promises.push(proxy.toClient().get(`https://eigenphi.io/api/v1/signalFinder?tx=${tx._id}`, { headers: defaultHeaders, timeout: 15000 })
        .then((r) => r.data)
        .catch((e) => null));
    }
    const results = await Promise.all(promises);
    console.log(`Got signal info of ${results.length} bundles`);
    let i = 0;
    const updateTxs = [];
    const updateBundles = [];
    for (const res of results) {
      const tx = txs[i++];
      const bundleId = tx.eigenphy.bundleId;
      if (!res) {
        console.log(`Get signal of ${tx._id} error`, res);
        await mongoDb.transactionsCol.updateOne({ _id: tx._id }, {
          $set: {
            "eigenphy.signalScanned": true,
            "eigenphy.error": true,
          },
        });
        continue;
      }
      const signalTxs = [];
      for (const signal of (res.signals || [])) {
        updateTxs.push({
          updateOne: {
            filter: { _id: signal.signal_tx_hash },
            update: {
              $set: {
                blockNumber: signal.signal_block_number,
                transactionIndex: signal.signal_tx_index,
                "eigenphy.signalOfTx": tx._id,
                "eigenphy.signalBundle": bundleId,
                "eigenphy.signalType": 'arbitrage',
              },
            },
            upsert: true,
          }
        });
        signalTxs.push(signal.signal_tx_hash);
      }
      updateTxs.push({
        updateOne: {
          filter: { _id: tx._id },
          update: {
            $set: {
              "eigenphy.signalScanned": true
            },
          },
          upsert: true,
        }
      });
      updateBundles.push({
        updateOne: {
          filter: { _id: bundleId },
          update: {
            $set: {
              signalTxs: signalTxs,
            },
          },
        }
      });
    }

    if (updateBundles.length) {
      const resultBundles = await mongoDb.bundlesCol.bulkWrite(updateBundles);
      console.log('Updated bundles', resultBundles.modifiedCount);
    }
    if (updateTxs.length) {
      const resultTxs = await mongoDb.transactionsCol.bulkWrite(updateTxs);
      console.log('Updated txs', resultTxs.modifiedCount);
    }
    await sleep(1000);
  }
  console.log('All txs of arbitrage were updated!');
}
