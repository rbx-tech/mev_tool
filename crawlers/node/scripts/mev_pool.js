import { mongoDb } from "../../mongo.js";
import { initDoc } from "./utils.js";

async function reportPools(sheet) {
  const results = await mongoDb.transactionsCol.aggregate(
    [
      { $match: { 'eigenphy.tag': 'searcher' } },
      {
        $lookup: {
          from: 'bundles',
          localField: 'eigenphy.bundleId',
          foreignField: '_id',
          as: 'bundle'
        }
      },
      { $unwind: '$bundle' },
      {
        $match: {
          'bundle.mevAddress': '0x00000000009e50a7ddb7a7b0e2ee6604fd120e49',
          'bundle.timestamp': {
            $gt: 1725148800,
            $lt: 1727740800
          },
          'bundle.types': 'arbitrage'
        }
      },
      { $unwind: '$pools' },
      {
        $group: {
          _id: '$pools',
          count: { $sum: 1 }
        }
      },
      { $sort: { count: -1 } },
      { $limit: 900 },
      { $project: { _id: '$_id', count: 1 } },
      {
        $lookup: {
          from: 'pools',
          localField: '_id',
          foreignField: '_id',
          as: 'pool'
        }
      },
      { $unwind: '$pool' },
    ]).toArray();

  const startRow = 3;
  await sheet.loadCells(`B${startRow}:E${results.length + startRow}`);
  for (let i = 0; i < results.length; i++) {
    const v = results[i];
    sheet.getCellByA1(`B${i + startRow}`).value = v._id;
    sheet.getCellByA1(`C${i + startRow}`).value = v.pool.name || '';
    sheet.getCellByA1(`D${i + startRow}`).value = v.pool.protocol?.name || '';
    sheet.getCellByA1(`E${i + startRow}`).value = v.count || '';
  }
  console.log("Thống kê số pools phổ biến")
  console.table(results);
}


(async function () {
  await mongoDb.connect();
  const doc = await initDoc();
  const sheet = doc.sheetsByTitle['MevPools'];
  await reportPools(sheet);
  await sheet.saveUpdatedCells();
  process.exit();
})()
