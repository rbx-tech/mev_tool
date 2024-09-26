// import { mongoDb } from "../mongo.js";
// import axios from "axios";

// export async function run_crawl_signals() {
//   while (true) {
//     const docs = await (mongoDb.bundlesCol.find({signals: null}).limit(100).toArray());
//     const promises = [];
//     const httpsAgent = new HttpsProxyAgent({host: "proxyhost", port: "proxyport", auth: "username:password"})

//     promises.push(axios.get(`https://eigenphi.io/api/v1/signalFinder?tx=${id}`, {
//         headers: {'Host': 'eigenphi.io', 'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36'},
//         httpAgent: ,
//         httpsAgent: ,
//     }).catch((e) => null));
    
//   }
// }
