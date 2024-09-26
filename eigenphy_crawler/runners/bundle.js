import { initializeApp } from 'firebase/app';
import { getFirestore, collection, getDocs, getCountFromServer, startAfter, query, limit, getDoc, doc } from 'firebase/firestore';
import { mongoDb } from '../mongo.js';
import axios from 'axios';
import {sleep} from '../utils/index.js'

const firebaseConfig = {
    apiKey: "AIzaSyAvFmPvlucS0n9Itaw3h9taenFHM3u_-Js",
    authDomain: "arbitragescan.firebaseapp.com",
    projectId: "arbitragescan",
    storageBucket: "arbitragescan.appspot.com",
    messagingSenderId: "277078002419",
    appId: "1:277078002419:web:95b4adedbca3c884074586",
    measurementId: "G-5ZKJHYB829",
  };

export async function run_crawl_bundles() {
    await mongoDb.connect();

    const app = initializeApp(firebaseConfig);
    const fireStore = getFirestore(app);

    let lastCusor = await mongoDb.infoCol.findOne({ _id: 'cusor' });
    let cusorDoc = null;
    if (!lastCusor) {
        await mongoDb.infoCol.insertOne({_id: 'cusor', value: null});
    }
    lastCusor = lastCusor?.value;
    if (lastCusor) {
        cusorDoc = await getDoc(doc(collection(fireStore, 'alpha/ethereum/live-stream-2'), lastCusor));
    }
    
    const queryConstrants = [collection(fireStore, 'alpha/ethereum/live-stream-2')];
    const count = await getCountFromServer(query(...queryConstrants));
    const totalCnt = count.data().count;
    console.log('Total bundles', totalCnt);

    const processLimit = 1000;
    while (true) {
        console.log(`Start from cusor=${lastCusor}`);
        if (cusorDoc) {
            queryConstrants.push(startAfter(cusorDoc));
        }
        queryConstrants.push(limit(processLimit));
        const docs = (await getDocs(query(...queryConstrants))).docs;
        console.log(`Got ${docs.length} bundles`);

        if (docs.length == 0) {
            console.log('All bundles were crawled!');
            break;
        }

        let promises = [];
        // let signalProcmises = [];
        for (const doc of docs) {
            const id = doc.id;
            promises.push(axios.get(`https://storage.googleapis.com/eigenphi-ethereum-tx/${id}`).catch((e) => null));
            // signalProcmises.push(axios.get(`https://eigenphi.io/api/v1/signalFinder?tx=${id}`, {
            //     headers: {'Host': 'eigenphi.io', 'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36'}
            // }).catch((e) => null));
            if (promises.length >= processLimit) {
                const bundlesResults = await Promise.all(promises);
                // const signalResults = await Promise.all(signalProcmises);
                const raws = [];
                for (let i = 0; i< bundlesResults.length; i++) {
                    const bData = bundlesResults[i]?.data;
                    if (!bData) {
                        continue;
                    }
                    const id = bData.resultId;
                    // const sData = signalResults[i]?.data;
                    // const signals = (sData?.signals || []);
                    const victimTx = (bData.tokenFlowCharts || []).find((it) => it.sandwichRole == 'Victim')?.txMeta?.transactionHash;
                    raws.push({
                        _id: id,
                        signals: null,
                        victimTx: victimTx,
                        ...bData,
                    });
                }
                const result = await mongoDb.bundlesCol.insertMany(raws);
                console.log(`Inserted ${result.insertedCount} bundles`);

                cusorDoc = docs.at(-1);
                lastCusor = cusorDoc.id;   
                await mongoDb.infoCol.updateOne({_id: 'cusor'}, {$set: {value: lastCusor}});
                promises = [];
                // signalProcmises = [];
                await sleep(500);
            }
        }
        await sleep(2000);
    }

    process.exit(0);
}
