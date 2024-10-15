import { mongoDb } from "../mongo.js";
import { initDoc } from "../scripts/utils.js";

async function reportPopularBuilder() {
  const doc = await initDoc();
  const sheet = doc.sheetsByTitle['MevTokens'];
  console.log("-".repeat(80))

  const results = await mongoDb.transactionsCol.aggregate(
    [
      {
        $match: {
          "eigenphy.tag": 'searcher',
          revenue: {$ne: null},
          // "revenue.profitUsd": {$lt: 10000},
          // "pools.20": {$exists: 0},
          "pools.1": {$exists: 1},
        }
      },
      {
        $addFields: {
          poolSize: { $size: '$pools' }
        }
      },
      {
        $group: {
          _id: {
            $concat: [
              'pools_cnt_',
              { $toString: '$poolSize' }
            ]
          },
          profitUsd: {$avg: '$revenue.profitUsd'},
          revenueUsd: {$avg: '$revenue.revenueUsd'},
          costUsd: {$avg: '$revenue.costUsd'},
          count: { $sum: 1 }
        }
      },
      { $sort: { count: -1 } },
      {$limit: 20},
    ],
  ).toArray();

  const startRow = 3;
  await sheet.loadCells(`B${startRow}:F${results.length + startRow}`);

  for (let i = 0; i < results.length; i++) {
    const v = results[i];
    sheet.getCellByA1(`B${i + startRow}`).value = v._id;
    sheet.getCellByA1(`C${i + startRow}`).value = v.count;
    sheet.getCellByA1(`D${i + startRow}`).value = v.revenueUsd;
    sheet.getCellByA1(`E${i + startRow}`).value = v.costUsd;
    sheet.getCellByA1(`F${i + startRow}`).value = v.profitUsd;
  }
  await sheet.saveUpdatedCells();

  console.table(results);
}


(async function () {
  await mongoDb.connect();
  await reportPopularBuilder();
  process.exit();
})()
