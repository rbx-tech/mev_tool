import { mongoDb } from "../../mongo.js";
import { Proxy6 } from "../../utils/proxy6.js";
import {sleep} from '../../utils/index.js';

const limit = 20;

export async function crawlLibMevBundles() {
  let runningCnt = 0;
  const offset = await mongoDb.getInfo('libmev_current_offset', 0);
  let nextOffset = offset;
  console.log(`Start crawling libmev bundles...`);

  while (true) {
    const maxRunners = await mongoDb.getInfo('libmev_runners', 5);
    for (let i = 0; i < (maxRunners - runningCnt); i++) {
      runningCnt++;
      processReq(nextOffset).then(async (offset) => {
        const currentOffset = await mongoDb.getInfo('libmev_current_offset', 0);
        if (offset > currentOffset) {
          await mongoDb.setInfo('libmev_current_offset', offset)
        }
        runningCnt--;
      });
      nextOffset += limit;
    }
    await sleep(1000);
    const isEnable = await mongoDb.getInfo('libmev_enable', false);
    if (!isEnable) {
      break;
    }
  }

  const next_run = Date.now() + 3600000;  // 6h
  await mongoDb.setInfo('libmev_next_run', next_run);
  console.log('LibMev', `Runner stopped, next_run = ${next_run}`);
}


async function processReq(offset) {
  const libMevUrl = `https://api.libmev.com/v1/bundles?timestampRange=1663224162,1727927182&filterByTags=naked_arb,backrun,sandwich,liquidation&orderByDesc=block_number`;
  const proxy = Proxy6.genNew();

  const url = `${libMevUrl}&limit=${limit}&offset=${offset}`;
  const bundleUpdates = [];
  const txUpdates = [];

  const runnerId = `libmev_offset_${offset}`;
  console.log(runnerId, 'Request to', url);

  await mongoDb.runners.updateOne(
    { _id: runnerId },
    {
      $set: {
        runner: `libmev`,
        offset: offset,
        limit: limit,
        url: url,
        startedAt: Date.now(),
      }
    },
    { upsert: true }
  );

  try {
    const result = await proxy.toClient().get(url);
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
    console.log(runnerId, `Request from offset ${offset} error`, msg);
    await mongoDb.runners.updateOne({ _id: runnerId }, { $set: { status: 'ERROR', msg: msg }, $inc: {errorsCnt: 1} });
  }
  return offset;
}