import { mongoDb } from "../mongo.js";
import { initDoc } from "./utils.js"


async function reportRouters() {
  const doc = await initDoc();
  const sheet = doc.sheetsByTitle['Routers'];
  console.log("Thống kê số lượng routers")

  const results = await mongoDb.transactionsCol.aggregate([
    {
      $match: {
        tags: "victim",
        types: "arbitrage",
      }
    },
    {
      $group: {
        _id: "$contractName",
        count: { $sum: 1 },
      }
    },
    { $sort: { count: -1 } },
    { $limit: 900 }
  ]).toArray();

  const startRow = 3;
  await sheet.loadCells(`B${startRow}:C${results.length + startRow}`);
  for (let i = 0; i < results.length; i++) {
    const v = results[i];
    sheet.getCellByA1(`B${i + startRow}`).value = v._id || '(Unknown)';
    sheet.getCellByA1(`C${i + startRow}`).value = v.count;
  }
  await sheet.saveUpdatedCells();
  console.table(results);
}

(async function () {
  await mongoDb.connect();
  await reportRouters();
  process.exit();
})()
