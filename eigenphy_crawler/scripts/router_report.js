import { mongoDb } from "../mongo.js";
import { initDoc } from "./utils.js"


async function reportRouters() {
  const doc = await initDoc();
  const sheet = doc.sheetsByTitle['Routers'];
  console.log("Thống kê số lượng routers")

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
        _id: "$raw.to",
        count: { $sum: 1 },
      }
    },
    { $sort: { count: -1 } }
  ]).toArray();

  const startRow = 2;
  const tables = results.splice(0, 900);
  tables.push({ _id: '(Other)', count: results.reduce((acc, it) => acc + it.count, 0) });
  await sheet.loadCells(`C${startRow}:D${results.length + startRow}`);

  for (let i = 0; i < tables.length; i++) {
    const v = tables[i];
    sheet.getCell(i + startRow, 2).value = v._id || '(Unknown)';
    sheet.getCell(i + startRow, 3).value = v.count;
  }
  await sheet.saveUpdatedCells();
  console.table(tables);
}

(async function () {
  await mongoDb.connect();
  await reportRouters();
  process.exit();
})()
