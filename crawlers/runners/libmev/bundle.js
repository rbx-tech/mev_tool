import { mongoDb } from "../../mongo.js";
import { Proxy6 } from "../../utils/proxy6.js";
import {sleep} from '../../utils/index.js';

export async function crawlLibMevBundles() {
  let runningCnt = 0;
  console.log(`Start crawling libmev bundles...`);

  const limit = await mongoDb.getInfo('libmev_crawl_limit', 20);
  await mongoDb.runners.updateMany({status: 'RUNNING'}, {$set: {status: 'PENDING'}})

  while (true) {
    await sleep(3000);
    const isEnable = await mongoDb.getInfo('libmev_enable', false);
    if (!isEnable) {
      break;
    }

    const maxRunners = await mongoDb.getInfo('libmev_runners', 5);
    const avail = (maxRunners - runningCnt);
    if (avail <= 0) {
      continue;
    }
    const runners = await mongoDb.runners.find({status: {$nin: ['OK', 'RUNNING']}}).sort({offset: 1}).limit(avail).toArray();
    if (!runners.length) {
      const offsetRes = await mongoDb.runners.find({}).sort({offset: -1}).limit(1).toArray();
      let currentOffset = 0;
      if (offsetRes.length) {
        currentOffset = offsetRes[0].offset + limit;
      }

      let nextOffset = currentOffset;
      const updates = [];
      for (let index = 0; index < avail; index++) {
        const runnerId = `libmev_offset_${nextOffset}`;
        const url = `https://api.libmev.com/v1/bundles?timestampRange=1663224162,1727927182&filterByTags=naked_arb,backrun,sandwich,liquidation&orderByDesc=block_number`;
        updates.push({
          updateOne: {
            filter: { _id: runnerId },
            update: {
              $set: {
                _id: runnerId,
                runner: `libmev`,
                offset: nextOffset,
                limit: limit,
                url: `${url}&offset=${nextOffset}&limit=${limit}`,
                status: 'PENDING',
                startedAt: Date.now(),
              },
            },
            upsert: true,
          },
        });
        nextOffset += limit;
      }
      await mongoDb.runners.bulkWrite(updates);
      continue;
    }

    for(const runner of runners) {
      runningCnt++;
      processReq(runner).then(async () => {
        runningCnt--;
      }).catch((e) => console.log(e));
    }
  }

  const next_run = Date.now() + 3600000;  // 6h
  await mongoDb.setInfo('libmev_next_run', next_run);
  console.log('LibMev', `Runner stopped, next_run = ${next_run}`);
}

async function processReq(runner) {
  const proxy = Proxy6.genNew();
  const bundleUpdates = [];
  const txUpdates = [];
  const runnerId = runner._id;
  await mongoDb.runners.updateOne(
    { _id: runnerId },
    { $set: {status: 'RUNNING'} },
  );
  console.log(runnerId, 'Request to', runner.url);

  try {
    const result = await proxy.toClient().get(runner.url);
    const bundleRaws = result.data.data;
    const totalBundles = result.data.count || 0;
    console.log(runnerId, `Got ${bundleRaws.length} bundles`);

    for (const raw of bundleRaws) {
      const bundleId = raw.bundle_hash
      const txs = raw.txs || [];
      const types = (raw.tags || []).map((e) => e == 'naked_arb' ? 'arbitrage' : e);
      const bundle = {
        _id: bundleId,
        timestamp: raw.timestamp,
        blockNumber: raw.block_number,
        revenueUsd: raw.profit_usdc,
        costUsd: raw.tipped_usdc,
        profitUsd: raw.profit_margin > 0 ? (raw.profit_usdc * raw.profit_margin) : (raw.profit_usdc - raw.tipped_usdc),
        builderName: raw.extra_data,
        builderAddress: raw.builder_address,
        types: types,
        txs: txs,
        signalTxs: txs.filter((it) => !(raw.searcher_txs || []).includes(it)),
        searcherTxs: raw.searcher_txs,
        source: "libmev",
        mevAddress: raw.searcher_contract,
        rawData: raw,
      }
      bundleUpdates.push({
        updateOne: {
          filter: { _id: bundleId },
          update: {
            $set: bundle,
          },
          upsert: true,
        }
      });

      for (const txHash of txs) {
        const tag = raw.searcher_txs.includes(txHash) ? 'searcher' : 'victim';
        const txData = {
          _id: txHash,
          blockNumber: bundle.blockNumber,
          timestamp: bundle.timestamp,
          libMev: {
            bundleId: bundleId,
            tag: tag,
            types: types,
          }
        }
        txUpdates.push({
          updateOne: {
            filter: { _id: txHash },
            update: {
              $set: txData,
              $addToSet: {
                bundleIds: bundleId,
                sources: 'libmev',
                tags: tag,
                types: {$each: types},
              }
            },
            upsert: true,
          }
        })
      }
    }

    if (bundleUpdates.length) {
      await mongoDb.bundlesCol.bulkWrite(bundleUpdates);
      console.log(runnerId, `Upserted ${bundleUpdates.length} bundles`);
    }
    if (bundleUpdates.length) {
      await mongoDb.transactionsCol.bulkWrite(txUpdates);
      console.log(runnerId, `Upserted ${txUpdates.length} txs`);
    }

    await Promise.all([
      mongoDb.setInfo('libmev_total_bundles', totalBundles),
      mongoDb.runners.updateOne({ _id: runnerId }, { $set: { status: 'OK' } }),
    ]);
  } catch (e) {
    const msg = e?.response?.data;
    console.log(runnerId, `Request from offset ${bundle.offset} error`, msg);
    await mongoDb.runners.updateOne({ _id: runnerId }, { $set: { status: 'ERROR', msg: msg }, $inc: {errorsCnt: 1} });
  }
}