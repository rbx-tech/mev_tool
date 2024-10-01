import { mongoDb } from "../mongo.js";
import { initDoc } from "./utils.js";

async function reportRouters() {
  const doc = await initDoc();
  const sheet = doc.sheetsByTitle['Transactions'];
  console.log("Thống kê lượng transactions")

  const results = await mongoDb.bundlesCol.aggregate([
    {
      $group: {
        _id: {
          "$dateToString": {
            "format": "%Y-%m",
            "date": { "$toDate": { "$multiply": ["$timestamp", 1000] } }
          }
        },
        victim: {
          '$sum': {$cond: [{$eq: ['$signalTxs', null]}, 0, {$size: "$signalTxs"}]}
        },
        searcher: {
          '$sum': {$cond: [{$eq: ['$searcherTxs', null]}, 0, {$size: "$searcherTxs"}]}
        },
      }
    },
    { $sort: {_id: -1} }
  ]).toArray();
  const startRow = 2;
  await sheet.loadCells(`B${startRow}:D${results.length + startRow}`);

  for (let i = 0; i < results.length; i++) {
    const v = results[i];
    sheet.getCell(i + startRow, 1).value = v._id || 'null';
    sheet.getCell(i + startRow, 2).value = v.searcher;
    sheet.getCell(i + startRow, 3).value = v.victim;
  }
  await sheet.saveUpdatedCells();
  console.table(results);
}

(async function () {
  await mongoDb.connect();
  await reportRouters();
  process.exit();
})()
