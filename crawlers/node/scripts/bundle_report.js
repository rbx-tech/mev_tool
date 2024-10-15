import { mongoDb } from "../mongo.js";
import { initDoc } from "./utils.js";


async function reportMev(sheet) {
  const startRow = 3;
  const mevResults = await mongoDb.bundlesCol.aggregate([
    {
      $match: {
        types: "arbitrage",
        source: "eigenphy"
      }
    },
    {
      $group: {
        _id: "$mevAddress",
        revenue: { $sum: "$revenueUsd" },
        profit: { $sum: "$profitUsd" },
        cost: { $sum: "$costUsd" },
      },
    },
    {
      $sort: {
        revenue: -1,
      }
    },
  ]).toArray();

  const top30 = mevResults.splice(0, 30);
  top30.push(mevResults.reduce((acc, it) => ({
    _id: 'Other',
    revenue: (acc.revenue || 0) + Number(it.revenue) || 0,
    profit: (acc.profit || 0) + Number(it.profit) || 0,
    cost: (acc.cost || 0) + Number(it.cost),
  }), {}));

  await sheet.loadCells(`B${startRow}:E${30 + startRow}`);
  for (let i = 0; i < 31; i++) {
    const v = top30.at(i);
    sheet.getCellByA1(`B${i + startRow}`).value = v?._id;
    sheet.getCellByA1(`C${i + startRow}`).value = Number(v?.revenue) || '';
    sheet.getCellByA1(`D${i + startRow}`).value = Number(v.cost);
    sheet.getCellByA1(`E${i + startRow}`).value = Number(v?.profit) || '';
  }
  console.table(top30);
}

async function reportProfitByMonths(sheet) {
  console.log("Thống kê profit theo từng tháng (USD)")
  const monthResults = await mongoDb.bundlesCol.aggregate([
    {
      $match: {
        types: "arbitrage",
        source: "eigenphy",
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
        libMev: {
          $sum: {
            $cond: [{ $eq: ["$source", "libmev"] }, 1, 0]
          }
        },
        eigenphy: {
          $sum: {
            $cond: [{ $eq: ["$source", "eigenphy"] }, 1, 0]
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

  const startRow = 3;
  await sheet.loadCells(`M30:H31`);
  await sheet.loadCells(`G${startRow}:J${monthResults.length + startRow}`);
  for (let i = 0; i < monthResults.length; i++) {
    const v = monthResults[i];
    sheet.getCellByA1(`G${i + startRow}`).value = v._id;
    sheet.getCellByA1(`H${i + startRow}`).value = Number(v.revenue) || 0;
    sheet.getCellByA1(`I${i + startRow}`).value = Number(v.cost) || 0;
    sheet.getCellByA1(`J${i + startRow}`).value = Number(v.profit) || 0;
  }

  sheet.getCellByA1('M30').value = monthResults.reduce((acc, it) => acc + it.eigenphy, 0);
  sheet.getCellByA1('M31').value = monthResults.reduce((acc, it) => acc + it.libMev, 0);
  console.table(monthResults);
}


(async function () {
  await mongoDb.connect();
  const doc = await initDoc();
  const sheet = doc.sheetsByTitle['Bundles'];

  await reportMev(sheet);
  await reportProfitByMonths(sheet);

  await sheet.loadCells('O30');
  sheet.getCellByA1('O30').value = new Date().toLocaleString();

  await sheet.saveUpdatedCells();
  process.exit();
})()
