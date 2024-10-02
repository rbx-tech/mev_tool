import { mongoDb } from "../mongo.js";
import { initDoc } from "./utils.js";


async function reportTokens(sheet) {
  const results = await mongoDb.transactionsCol.aggregate([
    {
      $match: {
        $or: [
          { "eigenphy.tag": "victim" },
          { "libMev.tag": "victim" },
        ]
      }
    },
    { $unwind: "$tokens" },
    {
      $group: {
        _id: "$tokens",
        count: { $sum: 1 }
      }
    },
    {
      $sort: { count: -1 },
    },
    { $limit: 1000 },
    {
      $project: {
        token: "$_id",
        count: 1,
        _id: 0
      }
    }
  ]).toArray();


  const startRow = 3;
  await sheet.loadCells(`H${startRow}:J${results.length + startRow}`);
  const tokens = (await mongoDb.tokensCol.find({ _id: { $in: results.map((it) => it.token) } }).toArray()).reduce((acc, it) => {
    acc[it._id] = it;
    return acc;
  }, {});

  for (let i = 0; i < results.length; i++) {
    const v = results[i];
    const p = tokens[v.token];
    sheet.getCellByA1(`H${i + startRow}`).value = p?.symbol;
    sheet.getCellByA1(`I${i + startRow}`).value = v.token;
    sheet.getCellByA1(`J${i + startRow}`).value = v.count;
  }
  console.log("Thống kê số tokens phổ biến")
  console.table(results);
}

async function reportPools(sheet) {
  const results = await mongoDb.transactionsCol.aggregate([
    {
      $match: {
        $or: [
          { "eigenphy.tag": "victim" },
          { "libMev.tag": "victim" },
        ]
      }
    },
    { $unwind: "$pools" },
    {
      $group: {
        _id: "$pools",
        count: { $sum: 1 }
      }
    },
    {
      $sort: { count: -1 },
    },
    { $limit: 1000 },
    {
      $project: {
        pool: "$_id",
        count: 1,
        _id: 0
      }
    }
  ]).toArray();

  const startRow = 3;
  await sheet.loadCells(`B${startRow}:E${results.length + startRow}`);
  const pools = (await mongoDb.poolsCol.find({ _id: { $in: results.map((it) => it.pool) } }).toArray()).reduce((acc, it) => {
    acc[it._id] = it;
    return acc;
  }, {});

  for (let i = 0; i < results.length; i++) {
    const v = results[i];
    const p = pools[v.pool];
    sheet.getCellByA1(`B${i + startRow}`).value = p?.name;
    sheet.getCellByA1(`C${i + startRow}`).value = v.pool;
    sheet.getCellByA1(`D${i + startRow}`).value = p?.protocol;
    sheet.getCellByA1(`E${i + startRow}`).value = v.count;
  }
  console.log("Thống kê số pools phổ biến")
  console.table(results);
}

async function reportProtocols(sheet) {
  const results = await mongoDb.transactionsCol.aggregate([
    {
      $match: {
        $or: [
          { "eigenphy.tag": "victim" },
          { "libMev.tag": "victim" },
        ]
      }
    },
    { $unwind: "$protocols" },
    {
      $group: {
        _id: {
          $cond: [{$in: ["$protocols", [null, '']]}, "(Unkown)" ,"$protocols"]
        },
        count: { $sum: 1 }
      }
    },
    {
      $sort: { count: -1 },
    },
    {
      $project: {
        protocol: "$_id",
        count: 1,
        _id: 0
      }
    }
  ]).toArray();

  const startRow = 3;
  await sheet.loadCells(`M${startRow}:N${results.length + startRow}`);
  for (let i = 0; i < results.length; i++) {
    
    const v = results[i];
    sheet.getCellByA1(`M${i + startRow}`).value = v.protocol;
    sheet.getCellByA1(`N${i + startRow}`).value = v.count;
  }
  console.log("Thống kê số protocols phổ biến")
  console.table(results);
}


(async function () {
  await mongoDb.connect();
  const doc = await initDoc();
  const sheet = doc.sheetsByTitle['Pools'];
  await Promise.all([
    reportPools(sheet),
    reportTokens(sheet),
    reportProtocols(sheet),
  ]);
  await sheet.saveUpdatedCells();
  process.exit();
})()
