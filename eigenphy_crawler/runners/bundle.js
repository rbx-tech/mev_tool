import { initializeApp } from 'firebase/app';
import { getFirestore, collection, getDocs, getCountFromServer, startAfter, query, limit, getDoc, doc } from 'firebase/firestore';
import { mongoDb } from '../mongo.js';
import axios from 'axios';
import { sleep } from '../utils/index.js'

const firebaseConfig = {
    apiKey: "AIzaSyAvFmPvlucS0n9Itaw3h9taenFHM3u_-Js",
    authDomain: "arbitragescan.firebaseapp.com",
    projectId: "arbitragescan",
    storageBucket: "arbitragescan.appspot.com",
    messagingSenderId: "277078002419",
    appId: "1:277078002419:web:95b4adedbca3c884074586",
    measurementId: "G-5ZKJHYB829",
};

export async function runCrawlBundles() {
    const app = initializeApp(firebaseConfig);
    const fireStore = getFirestore(app);

    let lastCusor = await getLastCusor();
    let cusorDoc = null;
    if (lastCusor) {
        cusorDoc = await getDoc(doc(collection(fireStore, 'alpha/ethereum/live-stream-2'), lastCusor));
    }

    const queryConstrants = [collection(fireStore, 'alpha/ethereum/live-stream-2')];
    const count = await getCountFromServer(query(...queryConstrants));
    const totalCnt = count.data().count;
    console.log('Total bundles', totalCnt);

    while (true) {
        const processLimit = await getLimit();

        console.log(`Start from cusor=${lastCusor}`);
        if (cusorDoc) {
            queryConstrants.push(startAfter(cusorDoc));
        }
        queryConstrants.push(limit(processLimit));
        const docs = (await getDocs(query(...queryConstrants))).docs;
        console.log(`Got ${docs.length} bundles from eigenphy`);

        if (docs.length == 0) {
            console.log('All bundles were crawled!');
            break;
        }

        let promises = [];
        for (const doc of docs) {
            const id = doc.id;
            const docData = doc.data();
            const insertedDoc = await mongoDb.bundlesCol.findOne({ _id: id });
            if (insertedDoc) {
                if (!insertedDoc.rawData) {
                    promises.push((async () => [docData, insertedDoc, true])());
                }
            } else {
                promises.push((async () => {
                    const res = await axios.get(`https://storage.googleapis.com/eigenphi-ethereum-tx/${id}`).then().catch((e) => null);
                    return [docData, res?.data, false]
                })());
            }
        }

        if (!promises.length) {
            continue;
        }

        const bundlesResults = await Promise.all(promises);
        const bundles = [];
        const tokens = {};
        const pools = {};
        let transactions = {};
        let replaceCnt = 0;
        for (let i = 0; i < bundlesResults.length; i++) {
            let [docData, rawData, isExisted] = bundlesResults[i];
            if (!rawData) {
                continue;
            }
            for (const p of docData?.poolsInfo || []) {
                pools[p.address] = {
                    _id: p.address,
                    protocol: p.protocol?.name,
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
            const [bundle, txDetails] = parseRawData(rawData, docData);
            transactions = {
                ...transactions,
                ...txDetails,
            }
            if (isExisted) {
                replaceCnt += 1;
                await mongoDb.bundlesCol.replaceOne({_id: bundle._id}, bundle);
            } else {
                bundles.push(bundle);
            }
        }

        if (bundles.length) {
            const result = await mongoDb.bundlesCol.insertMany(bundles);
            console.log(`Inserted ${result.insertedCount}, replace ${replaceCnt} bundles`);
        }
        if (Object.keys(pools).length) {
            const existsIds = await mongoDb.poolsCol.distinct('_id', {_id: {$in: Object.keys(pools)}});
            for (const id of existsIds) {
                delete pools[id];
            }
            const poolsList = Object.values(pools);
            if (poolsList.length) {
                const result = await mongoDb.poolsCol.insertMany(poolsList);
                console.log(`Inserted ${result.insertedCount} pools`);
            }
        }

        if (Object.keys(tokens).length) {
            const existsIds = await mongoDb.tokensCol.distinct('_id', {_id: {$in: Object.keys(tokens)}});
            for (const id of existsIds) {
                delete tokens[id];
            }
            const tokensList = Object.values(tokens);
            if (tokensList.length) {
                const result = await mongoDb.tokensCol.insertMany(tokensList);
                console.log(`Inserted ${result.insertedCount} tokens`);
            }
        }

        if (Object.keys(transactions).length) {
            const existsIds = await mongoDb.transactionsCol.distinct('_id', {_id: {$in: Object.keys(transactions)}});
            for (const id of existsIds) {
                delete transactions[id];
            }
            const transactionsList = Object.values(transactions);
            if (transactionsList.length) {
                const result = await mongoDb.transactionsCol.insertMany(transactionsList);
                console.log(`Inserted ${result.insertedCount} transactions`);
            }
        }

        promises = [];
        cusorDoc = docs.at(-1);
        lastCusor = cusorDoc.id;
        setLastCusor(lastCusor);
        await sleep(2000);
    }

    process.exit(0);
}


async function getLimit() {
    let limit = (await mongoDb.infoCol.findOne({ _id: 'eigenphy_crawl_limit' }))?.value;
    if (!limit) {
        limit = 1000;
        await mongoDb.infoCol.insertOne({ _id: 'eigenphy_crawl_limit', value: limit });
    }
    return limit;
}

async function getLastCusor() {
    let lastCusor = await mongoDb.infoCol.findOne({ _id: 'eigenphy_cusor' });
    if (!lastCusor) {
        await mongoDb.infoCol.insertOne({ _id: 'eigenphy_cusor', value: null });
    }
    return lastCusor?.value;
}

async function setLastCusor(cusor) {
    await mongoDb.infoCol.updateOne({ _id: 'eigenphy_cusor' }, { $set: { value: cusor } });
}


function parseRawData(rawData, docData) {
    const id = rawData.resultId;
    delete rawData.pools;
    delete rawData.tokens;
    delete rawData.victimTx;
    delete rawData._id;
    rawData = {
        ...rawData,
        pools: docData?.poolsInfo || [],
        tokens: docData?.tokens || [],
    }
    const poolIds = rawData.pools.map((e) => e.address);
    const tokenIds = rawData.tokens.map((e) => e.address);
    const txHash = rawData.txMeta?.transactionHash;

    let txIds = null;
    let searcherTxs = [txHash];
    let signalTxs = null;

    let txDetails = {};

    if (rawData.tokenFlowCharts?.length) {
        txIds = [];
        searcherTxs = [];
        signalTxs = [];
        for (const fl of rawData.tokenFlowCharts) {
            const txHash = fl.txMeta.transactionHash;
            const tx = {
                _id: txHash,
                blockNumber: fl.txMeta.blockNumber,
                bundleId: id,
                transactionIndex: fl.txMeta.transactionIndex,
                tag: "victim",
                protocols: null,
                sandwichRole: fl.sandwichRole.toLowerCase(),
                contractName: null,
                inputDecoded: null,
                detailRaw: null,
            };
            txIds.push(txHash)
            if (fl.sandwichRole == 'Victim') {
                signalTxs.push(txHash)
            } else {
                tx.tag = "searcher";
                searcherTxs.push(txHash)
            }
            txDetails[txHash] = tx;
        }
        txIds = rawData.tokenFlowCharts.map((e) => e.txMeta.transactionHash);
        signalTxs = rawData.tokenFlowCharts.map((e) => e.sandwichRole == 'Victim' ? e.txMeta.transactionHash : null).filter((e) => e);
    } else {
        txDetails[txHash] = {
            _id: txHash,
            bundleId: id,
            blockNumber: rawData.txMeta.blockNumber,
            transactionIndex: rawData.txMeta.transactionIndex,
            tag: "victim",
            protocols: null,
            contractName: null,
            inputDecoded: null,
            detailRaw: null,
        };
    }

    const bundle = {
        _id: id,
        timestamp: rawData.txMeta.blockTimestamp,
        blockNumber: rawData.txMeta.blockNumber,
        revenueUsd: parseFloat(rawData.summary.revenue),
        costUsd: parseFloat(rawData.summary.cost),
        profitUsd: parseFloat(rawData.summary.profit),
        tippedEth: null,
        burnedEth: null,
        profitRaws: null,
        builderName: null,
        builderAddress: null,
        types: (rawData.summary?.types || []).map((e) => e.toLowerCase()),
        tokens: tokenIds,
        pools: poolIds,
        useFlashloan: docData.useFlashloan,
        txs: txIds,
        signalTxs: signalTxs,
        searcherTxs: searcherTxs,
        source: "eigenphy",
        rawData: rawData,
    };
    return [bundle, txDetails]
}
