import { initializeApp } from 'firebase/app';
import { getFirestore, collection, getDocs, getCountFromServer, startAfter, query, limit, getDoc, orderBy, doc } from 'firebase/firestore';
import { mongoDb } from '../../mongo.js';
import axios from 'axios';
import { sleep, removeDuplicate } from '../../utils/index.js'
import { Proxy4 } from "../../utils/proxy4.js";

const firebaseConfig = {
    apiKey: "AIzaSyAvFmPvlucS0n9Itaw3h9taenFHM3u_-Js",
    authDomain: "arbitragescan.firebaseapp.com",
    projectId: "arbitragescan",
    storageBucket: "arbitragescan.appspot.com",
    messagingSenderId: "277078002419",
    appId: "1:277078002419:web:95b4adedbca3c884074586",
    measurementId: "G-5ZKJHYB829",
};

export async function runCrawlEigenphyBundles() {
    console.log('Eigenphy', 'Start crawling eigenphy bundles...');
    const app = initializeApp(firebaseConfig);
    const fireStore = getFirestore(app);

    let lastCusor = await mongoDb.getInfo('eigenphy_cusor');

    const queryConstrants = [collection(fireStore, 'alpha/ethereum/live-stream-2')];
    const count = await getCountFromServer(query(...queryConstrants));
    const totalCnt = count.data().count;
    console.log('Eigenphy', 'Total bundles', totalCnt);

    while (true) {
        const isEnable = await mongoDb.getInfo('eigenphy_enable', false);
        if (!isEnable) {
            break;
        }

        const processLimit = await mongoDb.getInfo('eigenphy_crawl_limit', 1000);
        console.log('Eigenphy', `Start from cusor=${lastCusor}`);
        const constrants = [...queryConstrants];

        constrants.push(orderBy('timestamp'), limit(processLimit));
        if (lastCusor) {
            constrants.push(startAfter(lastCusor));
        }
        const docs = (await getDocs(query(...constrants))).docs;
        console.log('Eigenphy', `Got ${docs.length} bundles from eigenphy`);

        if (docs.length == 0) {
            console.log('Eigenphy', 'All bundles were crawled!');
            await mongoDb.setInfo('eigenphy_cusor', null);
            break;
        }

        let promises = [];
        for (const doc of docs) {
            const id = doc.id;
            const docData = doc.data();
            promises.push((async () => {
                const res = await axios.get(`https://storage.googleapis.com/eigenphi-ethereum-tx/${id}`).then().catch((e) => null);
                return [docData, res?.data, false]
            })());
        }

        if (!promises.length) {
            continue;
        }

        const bundlesResults = await Promise.all(promises);
        const tokens = {};
        const pools = {};
        let bundleWrites = {};
        let transactionWrites = {};
        let needCheckSignals = [];
        for (let i = 0; i < bundlesResults.length; i++) {
            let [docData, rawData] = bundlesResults[i];
            if (!rawData) {
                continue;
            }
            for (const p of docData?.poolsInfo || []) {
                pools[p.address] = {
                    _id: p.address,
                    protocol: p.protocol,
                    name: p.name,
                    symbol: p.symbol,
                    tokens: p.tokens,
                };
            }
            for (const t of docData?.tokens || []) {
                tokens[t.address] = {
                    _id: t.address,
                    symbol: t.symbol,
                    decimals: t.decimals,
                };
            }
            const [bundle, txUpdates] = await parseRawData(rawData, docData);
            for (const txHash of Object.keys(txUpdates)) {
                const update = txUpdates[txHash];
                if (update.signalKey) {
                    needCheckSignals.push({
                        txHash: update.signalKey,
                        bundleId: update.updateOne.update.$set['eigenphy.bundleId']
                    });
                    delete txUpdates[txHash].signalKey;
                }
            }
            transactionWrites = {
                ...transactionWrites,
                ...txUpdates,
            }
            bundleWrites[bundle.updateOne.update.$set._id] = bundle;
        }

        if (needCheckSignals.length) {
            const results = await detectSignals(needCheckSignals, transactionWrites, bundleWrites);
            transactionWrites = results[0]
            bundleWrites = results[1]
            needCheckSignals = [];
        }

        if (Object.keys(bundleWrites).length) {
            const writes = Object.values(bundleWrites);
            await mongoDb.bundlesCol.bulkWrite(writes);
            console.log('Eigenphy', `Upserted ${writes.length} bundles`);
        }
        if (Object.keys(pools).length) {
            const existsIds = await mongoDb.poolsCol.distinct('_id', { _id: { $in: Object.keys(pools) } });
            for (const id of existsIds) {
                delete pools[id];
            }
            const poolsList = Object.values(pools);
            if (poolsList.length) {
                const result = await mongoDb.poolsCol.insertMany(poolsList);
                console.log('Eigenphy', `Inserted ${result.insertedCount} pools`);
            }
        }

        if (Object.keys(tokens).length) {
            const existsIds = await mongoDb.tokensCol.distinct('_id', { _id: { $in: Object.keys(tokens) } });
            for (const id of existsIds) {
                delete tokens[id];
            }
            const tokensList = Object.values(tokens);
            if (tokensList.length) {
                const result = await mongoDb.tokensCol.insertMany(tokensList);
                console.log('Eigenphy', `Inserted ${result.insertedCount} tokens`);
            }
        }

        if (Object.keys(transactionWrites).length) {
            const txWrites = Object.values(transactionWrites);
            if (txWrites.length) {
                await mongoDb.transactionsCol.bulkWrite(txWrites);
                console.log('Eigenphy', `Upserted ${txWrites.length} transactions`);
            }
        }

        promises = [];
        const lastData = docs.at(-1).data();
        lastCusor = lastData.timestamp;
        await mongoDb.setInfo('eigenphy_cusor', lastCusor);
        await sleep(2000);
    }
    const next_run = Date.now() + 3600000;  // 6h
    await mongoDb.setInfo('eigenphy_next_run', next_run);
    console.log('Eigenphy', `Runner stopped, next_run = ${next_run}`);
}

async function detectSignals(txs, transactionWrites, bundleWrites) {
    const defaultHeaders = {
        'Host': 'eigenphi.io',
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
    };

    const promises = [];
    for (const tx of txs) {
        const proxy = await Proxy4.genNew();
        promises.push(proxy.toClient().get(`https://eigenphi.io/api/v1/signalFinder?tx=${tx.txHash}`, { headers: defaultHeaders, timeout: 15000 })
            .then((r) => r.data)
            .catch((e) => null));
    }
    console.log('Eigenphy', `Checking signal of ${promises.length} tx...`);
    const results = await Promise.all(promises);
    console.log('Eigenphy', `Got signal info of ${results.length} bundles`);

    let i = 0;
    for (const res of results) {
        const tx = txs[i++];
        const txIds = [];
        const bundleId = tx.bundleId;
        const txHash = tx.txHash;
        txIds.push(txHash);
        if (!res) {
            transactionWrites[txHash].updateOne.update.$set["eigenphy.error"] = true;
            transactionWrites[txHash].updateOne.update.$set["eigenphy.signalScanned"] = true;
            continue;
        }
        const signalTxs = [];
        for (const signal of (res.signals || [])) {
            const signalHash = signal.signal_tx_hash;
            txIds.push(signalHash);
            signalTxs.push(signalHash);
            transactionWrites[txHash].updateOne.update.$set["eigenphy.signalScanned"] = true;

            if (transactionWrites[signalHash]) {
                transactionWrites[signalHash].updateOne.update.$addToSet.types.$each.push('arbitrage');
                transactionWrites[signalHash].updateOne.update.$addToSet.bundleIds.$each.push(bundleId);
                transactionWrites[signalHash].updateOne.update.$addToSet.tags.$each.push('victim');
                transactionWrites[signalHash].updateOne.update.$set['eigenphy.signalOfTx'] = txHash;
                transactionWrites[signalHash].updateOne.update.$set['eigenphy.signalBundle'] = bundleId;
            } else {
                transactionWrites[signalHash] = {
                    updateOne: {
                        filter: { _id: signalHash },
                        update: {
                            $set: {
                                blockNumber: signal.signal_block_number,
                                transactionIndex: signal.signal_tx_index,
                                "eigenphy.signalOfTx": txHash,
                                "eigenphy.signalBundle": bundleId,
                                "eigenphy.signalType": 'arbitrage',
                            },
                            $addToSet: {
                                types: {$each: ['arbitrage']},
                                bundleIds: {$each: [bundleId]},
                                tags: {$each: ['victim']},
                            }
                        },
                        upsert: true,
                    }
                };
            }
        }
        if (bundleWrites[bundleId]) {
            bundleWrites[bundleId].updateOne.update.$set['txs'] = txIds;
            bundleWrites[bundleId].updateOne.update.$set['signalTxs'] = signalTxs;
        } else {
            bundleWrites[bundleId] = {
                updateOne: {
                    filter: { _id: bundleId },
                    update: {
                        $addToSet: {
                            txs: {$each: txIds},
                            signalTxs: {$each: signalTxs},
                        },
                    },
                }
            }
        }
    }

    return [transactionWrites, bundleWrites]
}

async function parseRawData(rawData, docData) {
    const id = rawData.resultId;
    delete rawData.pools;
    delete rawData.tokens;
    delete rawData.victimTx;
    delete rawData._id;
    const txHash = rawData.txMeta?.transactionHash;

    let txIds = [txHash];
    let searcherTxs = [txHash];
    let signalTxs = null;
    let txDetails = {};

    const poolIds = (docData?.poolsInfo || []).map((e) => e.address);
    const tokenIds = (docData?.tokens || []).map((e) => e.address);
    const protocols = removeDuplicate((docData?.poolsInfo || []).filter((e) => e).map((e) => e.protocol?.name || e.address));

    if (rawData.tokenFlowCharts?.length) {
        searcherTxs = [];
        signalTxs = [];
        for (const fl of rawData.tokenFlowCharts) {
            const txHash = fl.txMeta.transactionHash;
            const txData = {
                _id: txHash,
                blockNumber: fl.txMeta.blockNumber,
                timestamp: fl.txMeta.blockTimestamp,
                transactionIndex: fl.txMeta.transactionIndex,
                "eigenphy.bundleId": id,
                "sandwichRole": fl.sandwichRole.toLowerCase(),
            };
            let addToSetsData = {
                types: { $each: ['sandwich'] },
                bundleIds: { $each: [id] },
                tags: { $each: [] },
                sources: 'eigenphy',
            };
            if (txHash == id) {
                addToSetsData = {
                    tokens: { $each: tokenIds },
                    pools: { $each: poolIds },
                    protocol: { $each: protocols },
                }
            }
            if (fl.sandwichRole == 'Victim') {
                signalTxs.push(txHash)
                addToSetsData.tags.$each.push("victim");
                txData["eigenphy.tag"] = "victim";
            } else {
                searcherTxs.push(txHash)
                addToSetsData.tags.$each.push("searcher");
                txData["eigenphy.tag"] = "searcher";
            }
            txDetails[txHash] = {
                updateOne: {
                    filter: { _id: txHash },
                    update: {
                        $set: txData,
                        $addToSet: addToSetsData,
                    },
                    upsert: true,
                },
            };
        }
        txIds = rawData.tokenFlowCharts.map((e) => e.txMeta.transactionHash);
        signalTxs = rawData.tokenFlowCharts.map((e) => e.sandwichRole == 'Victim' ? e.txMeta.transactionHash : null).filter((e) => e);
    } else {
        const txData = {
            _id: txHash,
            blockNumber: rawData.txMeta.blockNumber,
            timestamp: rawData.txMeta.blockTimestamp,
            transactionIndex: rawData.txMeta.transactionIndex,
            "eigenphy.bundleId": id,
            "eigenphy.tag": "searcher",
        };
        txDetails[txHash] = {
            signalKey: txHash,
            updateOne: {
                filter: { _id: txHash },
                update: {
                    $set: txData,
                    $addToSet: {
                        sources: 'eigenphy',
                        protocols: { $each: protocols },
                        tokens: { $each: tokenIds },
                        pools: { $each: poolIds },
                        tags: { $each: ['searcher'] },
                        types: { $each: ['arbitrage'] },
                        bundleIds: { $each: [id] }
                    }
                },
                upsert: true
            }
        };
    }

    const bundle = {
        _id: id,
        timestamp: rawData.txMeta.blockTimestamp,
        blockNumber: rawData.txMeta.blockNumber,
        revenueUsd: Number(rawData.summary.revenue),
        costUsd: Number(rawData.summary.cost),
        profitUsd: Number(rawData.summary.profit),
        types: (rawData.summary?.types || []).map((e) => e.toLowerCase()),
        useFlashloan: docData.useFlashloan,
        txs: txIds,
        searcherTxs: searcherTxs,
        source: "eigenphy",
        mevAddress: rawData.txMeta.transactionToAddress,
        rawData: {
            ...rawData,
            tokens: docData?.tokens || [],
            poolsInfo: docData?.poolsInfo || [],
        },
    };
    if (signalTxs) {
        bundle.signalTxs = signalTxs;
    }
    const bundleUpdate = {
        updateOne: {
            filter: { _id: bundle._id },
            update: { 
                $set: bundle,
            },
            upsert: true,
        }
    };
    return [bundleUpdate, txDetails]
}
