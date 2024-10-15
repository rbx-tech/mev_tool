import { mongoDb } from "../mongo.js";
import { initDoc } from "./utils.js";

async function reportTxByMonths(sheet) {
  const results = await mongoDb.bundlesCol.aggregate([
    {
      $match: {
        types: "arbitrage"
      }
    },
    {
      $group: {
        _id: {
          "$dateToString": {
            "format": "%Y-%m",
            "date": { "$toDate": { "$multiply": ["$timestamp", 1000] } }
          }
        },
        victim: {
          '$sum': {$cond: [{$isArray: '$signalTxs'}, {$size: "$signalTxs"}, 0]}
        },
        searcher: {
          '$sum': {$cond: [{$isArray: '$signalTxs'}, {$size: "$searcherTxs"}, 0]}
        },
      }
    },
    { $sort: {_id: 1} }
  ]).toArray();
  const startRow = 3;
  await sheet.loadCells(`B${startRow}:D${results.length + startRow}`);

  for (let i = 0; i < results.length; i++) {
    const v = results[i];
    sheet.getCellByA1(`B${i + startRow}`).value = v._id;
    sheet.getCellByA1(`C${i + startRow}`).value = v.searcher;
    sheet.getCellByA1(`D${i + startRow}`).value = v.victim;
  }
  await sheet.saveUpdatedCells();
  console.log("Thống kê lượng transactions")
  console.table(results);
}

async function reportSwapFunc(sheet) {
  const results = await mongoDb.transactionsCol.aggregate([
    {
      $match: {
        tags: "victim",
        types: "arbitrage"
      }
    },
    {
      $group: {
        _id: "$inputDecoded.func",
        count: { $sum: 1 },
      }
    },
    {
      $sort: {count: -1}
    }
  ]).toArray();
  const startRow = 3;
  await sheet.loadCells(`P${startRow}:Q${results.length + startRow}`);

  for (let i = 0; i < results.length; i++) {
    const v = results[i];
    sheet.getCellByA1(`P${i + startRow}`).value = v._id || '(Unknown)';
    sheet.getCellByA1(`Q${i + startRow}`).value = v.count;
  }
  console.log("Thống kê số lượng functions")
  console.table(results);
}

(async function () {
  await mongoDb.connect();
  const doc = await initDoc();
  const sheet = doc.sheetsByTitle['Transactions'];

  await Promise.all([
    reportSwapFunc(sheet),
    reportTxByMonths(sheet),
  ]);
  await sheet.saveUpdatedCells();
  process.exit();
})()
