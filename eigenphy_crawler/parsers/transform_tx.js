import { mongoDb } from '../mongo.js'

async function parseTxTypesTags() {
  await mongoDb.transactionsCol.aggregate([
    {
      $match: {
        types: null,
        $or: [
          {"eigenphy": { $exists: 1 }},
          {"libMev": { $exists: 1 }}
        ]
      }
    },
    {
      $set: {
        tags: {
          $function: {
            body: "function(tags) { return [...new Set(tags)].filter((e) => e);}",
            args: [["$eigenphy.tag", "$libMev.tag"]],
            lang: "js"
          }
        },
        bunderIds: {
          $function: {
            body: "function(ids) { return [...new Set(ids)].filter((e) => e);}",
            args: [["$eigenphy.bundleId", "$libMev.bundleId"]],
            lang: "js"
          }
        },
        types: {
          $function: {
            body: "function(types) { return [...new Set(types)].filter((e) => e);}",
            args: [["$eigenphy.type", "$libMev.type"]],
            lang: "js"
          }
        },
      }
    },
    {
      $merge: {
        into: "transactions",
        whenMatched: "merge",
        whenNotMatched: "discard"
      }
    }
  ]).toArray();
  console.log('All documents were updated!')
}


(async function () {
  await mongoDb.connect();
  await parseTxTypesTags();
  process.exit();
})()