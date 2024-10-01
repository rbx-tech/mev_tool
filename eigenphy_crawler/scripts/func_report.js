import { mongoDb } from "../mongo.js";
import { initDoc } from "./utils.js";

async function reportSwapFunc() {
  const doc = await initDoc();
  const sheet = doc.sheetsByTitle['Functions'];
  console.log("Thống kê số lượng functions")

  const results = await mongoDb.transactionsCol.aggregate([
    {
      $match: {
        $or: [
          {
            "eigenphy.tag": "victim",
          },
          {
            "libMev.tag": "victim",
          }
        ]
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
  const startRow = 2;
  await sheet.loadCells(`B${startRow}:C${results.length + startRow}`);

  for (let i = 0; i < results.length; i++) {
    const v = results[i];
    sheet.getCell(i + startRow, 1).value = v._id || 'unknown';
    sheet.getCell(i + startRow, 2).value = v.count;
  }
  await sheet.saveUpdatedCells();
  console.table(results);
}

(async function () {
  await mongoDb.connect();
  await reportSwapFunc();
  process.exit();
})()
