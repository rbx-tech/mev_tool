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
                promises.push((async () => [docData, insertedDoc, true])());
            } else {
                promises.push((async () => {
                    const res = await axios.get(`https://storage.googleapis.com/eigenphi-ethereum-tx/${id}`).then().catch((e) => null);
                    return [docData, res?.data, false]
                })());
            }
        }

        const bundlesResults = await Promise.all(promises);
        const bundles = [];
        const tokens = {};
        const pools = {};
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
            const bundle = parseRawData(rawData, docData);
            if (isExisted) {
                replaceCnt += 1;
                await mongoDb.bundlesCol.replaceOne({_id: bundle._id}, bundle);
            } else {
                bundles.push(bundle);
            }
        }
        const result = await mongoDb.bundlesCol.insertMany(bundles);
        console.log(`Inserted ${result.insertedCount}, replace ${replaceCnt} bundles`);
        if (Object.keys(pools).length) {
            const existsIds = await mongoDb.poolsCol.distinct('_id', {_id: {$in: Object.keys(pools)}});
            for (const id of existsIds) {
                delete pools[id];
            }
            const result = await mongoDb.poolsCol.insertMany(Object.values(pools));
            console.log(`Inserted ${result.insertedCount} pools`);
        }

        if (Object.keys(tokens).length) {
            const existsIds = await mongoDb.tokensCol.distinct('_id', {_id: {$in: Object.keys(tokens)}});
            for (const id of existsIds) {
                delete tokens[id];
            }
            const result = await mongoDb.tokensCol.insertMany(Object.values(tokens));
            console.log(`Inserted ${result.insertedCount} tokens`);
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
    let txs = null;
    let searcherTxs = [rawData.txMeta.transactionHash];
    let signalTxs = null;

    if (rawData.tokenFlowCharts?.length) {
        let txs = [];
        let searcherTxs = [];
        let signalTxs = [];
        for (const fl of rawData.tokenFlowCharts) {
            const txHash = fl.txMeta.transactionHash;
            txs.push(txHash)
            if (fl.sandwichRole == 'Victim') {
                signalTxs.push(txHash)
            } else {
                searcherTxs.push(txHash)
            }
        }
        txs = rawData.tokenFlowCharts.map((e) => e.txMeta.transactionHash);
        signalTxs = rawData.tokenFlowCharts.map((e) => e.sandwichRole == 'Victim' ? e.txMeta.transactionHash : null).filter((e) => e);
    }

    return {
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
        txs: txs,
        signalTxs: signalTxs,
        searcherTxs: searcherTxs,
        source: "eigenphy",
        rawData: rawData,
    };
}