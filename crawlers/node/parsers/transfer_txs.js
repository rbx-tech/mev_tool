import { mongoDb, MongoDb } from '../mongo.js'

async function transferTxsFromOldDB() {
  const db = new MongoDb();
  await db.connect();
  while (true) {
    db.switchDb('mev');
    const unfillTxs = await db.transactionsCol.find({checkFilled: null}, {_id: 1}).limit(5000).toArray();
    if (!unfillTxs.length) {
      console.log('All txs are transfered!')
      break;
    }
    console.log(`Found ${unfillTxs.length} un-filled txs`);
    const txIds = unfillTxs.map((it) => it._id);
    await db.transactionsCol.updateMany({_id: {$in: txIds}}, {$set: {checkFilled: true}});

    db.switchDb('eigenphy');
    const txs = await db.transactionsCol.find({_id: {$in: txIds}, checkFilled: null, raw: {$ne: null}}).toArray();
    const updates = [];
    for(const tx of txs) {
      updates.push({
        updateOne: {
          filter: {_id: tx._id},
          update: {
            $set: {
              raw: tx.raw,
              toAddress: tx.raw.to,
              tokens: tx.tokens,
              // pools: tx.pools,
              // protocols: tx.protocols,
              volume: tx.volume,
              inputDecoded: tx.inputDecoded,
              checkFilled: true
            }
          }
        }
      });
    }
    db.switchDb('mev');
    if (updates.length) {
      const result = await db.transactionsCol.bulkWrite(updates);
      console.log(result);
    }
  }
  // await mongoDb.transactionsCol.updateMany({checkFilled: true}, {$unset: {checkFilled: 1}});
}


(async function () {
  await Promise.all([
    transferTxsFromOldDB(),
    transferTxsFromOldDB(),
    transferTxsFromOldDB(),
    transferTxsFromOldDB(),
  ]);
  process.exit();
})()