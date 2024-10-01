import { mongoDb } from "../mongo.js";
import { initDoc } from "./utils.js";

async function reportProfitByMonths() {
  const doc = await initDoc();
  const sheet = doc.sheetsByTitle['Profits'];
  console.log("Thống kê profit theo từng tháng (USD)")
  const results = await mongoDb.bundlesCol.aggregate([
    {
      $match: {
        revenueUsd: {$ne: null},
        profitUsd: {$ne: null},
        costUsd: {$ne: null},
        source: 'libmev'
      }
    },
    {
      $group: {
        _id: {
          "$dateToString": {
            "format": "%Y-%m",
            "date": { "$toDate": { "$multiply": [ "$timestamp", 1000 ] } }
          }
        },
        revenue: { $sum: "$revenueUsd" },
        profit: { $sum: "$profitUsd" },
        cost: { $sum: "$costUsd" },
      }
    },
    {
      $sort: {
        _id: -1,
      }
    }
  ]).toArray();
  const tables = results.map((e) => ({...e, 
    profit: Number(e.profit), 
    revenue: Number(e.revenue),
    cost: Number(e.cost),
  }))
  const startRow = 2;
  await sheet.loadCells(`B${startRow}:E${tables.length + startRow}`);

  for (let i = 0; i < tables.length; i++) {
    const v = tables[i];
    sheet.getCell(i + startRow, 1).value = v._id;
    sheet.getCell(i + startRow, 2).value = v.revenue;
    sheet.getCell(i + startRow, 3).value = v.cost;
    sheet.getCell(i + startRow, 4).value = v.profit;
  }
  await sheet.saveUpdatedCells();
  console.table(tables);
}


(async function () {
  await mongoDb.connect();
  await reportProfitByMonths();
  process.exit();
})()
