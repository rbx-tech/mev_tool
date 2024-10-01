import { mongoDb } from "../mongo.js";
import { initDoc } from "./utils.js";

async function reportPopularBuilder() {
  const doc = await initDoc();
  const sheet = doc.sheetsByTitle['Builders'];

  console.log("-".repeat(80))
  console.log("Thống kê builder phổ biến")
  const results = await mongoDb.bundlesCol.aggregate([
    {
      $group: {
        _id: "$builderAddress",
        count: { $sum: 1 },
      }
    },
    {
      $sort: {
        count: -1,
      }
    }
  ]).toArray();
  const top50 = results.splice(0, 50);
  const otherCnt = results.reduce((acc, it) => acc + it.count, 0);
  top50.push({_id: 'Other', count: otherCnt});

  const startRow = 2;
  await sheet.loadCells(`C${startRow}:D${top50.length + startRow}`);

  for (let i = 0; i < top50.length; i++) {
    const v = top50[i];
    sheet.getCell(i + startRow, 2).value = v._id || 'unknown';
    sheet.getCell(i + startRow, 3).value = v.count;
  }
  await sheet.saveUpdatedCells();

  console.table(top50);
}


(async function () {
  await mongoDb.connect();
  await reportPopularBuilder();
  process.exit();
})()
