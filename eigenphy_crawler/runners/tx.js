import { initializeApp } from 'firebase/app';
import { getFirestore, collection, getDocs, getCountFromServer, startAfter, query, limit, getDoc, doc } from 'firebase/firestore';
import { mongoDb } from '../mongo.js';
import axios from 'axios';
import { sleep, removeDuplicate } from '../utils/index.js'

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
    const docs = await getDoc(doc(collection(fireStore, 'alpha/ethereum/live-stream-2'), ''));
}
