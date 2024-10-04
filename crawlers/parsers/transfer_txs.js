import { mongoDb } from '../mongo.js'

async function transferTxsFromOldDB() {
  while (true) {
    mongoDb.switchDb('mev');
    const unfillTxs = await mongoDb.transactionsCol.find({raw: null, checkFilled: null}, {_id: 1}).sort({blockNumber: 1}).limit(10000).toArray();
    if (!unfillTxs.length) {
      console.log('All txs are transfered!')
      break;
    }
    console.log(`Found ${unfillTxs.length} un-filled txs`);
    mongoDb.switchDb('eigenphy');
    const txs = await mongoDb.transactionsCol.find({_id: {$in: unfillTxs.map((it) => it._id)}, raw: {$ne: null}}).toArray();
    const updates = [];
    for(const tx of txs) {
      updates.push({
        updateOne: {
          filter: {_id: tx._id},
          update: {
            $set: {
              raw: tx.raw,
              toAddress: tx.raw.to,
              inputDecoded: tx.inputDecoded,
              checkFilled: true
            }
          }
        }
      });
    }
    mongoDb.switchDb('mev');
    if (updates.length) {
      const result = await mongoDb.transactionsCol.bulkWrite(updates);
      console.log(result);
    }
  }
  // await mongoDb.transactionsCol.updateMany({checkFilled: true}, {$unset: {checkFilled: 1}});
}


(async function () {
  await mongoDb.connect();
  await transferTxsFromOldDB();
  process.exit();
})()