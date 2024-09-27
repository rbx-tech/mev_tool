import { mongoDb } from "../mongo.js";
import axios from "axios";
import { sleep } from "../utils/index.js";


export async function runCrawlSignals() {
  const defaultHeaders =  {
    'Host': 'eigenphi.io', 
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
  };
  while (true) {
    const docs = await (mongoDb.bundlesCol.find({signals: null, "summary.types": "Arbitrage"}).limit(100).toArray());
    const promises = [];
    
    for (const doc of docs) {
      promises.push(axios.get(`https://eigenphi.io/web3proxy/txReceipt?txHash=${doc._id}`, {headers: defaultHeaders, timeout: 15000}).then((r) => r.data).catch((e) => null));
    }
    const results = await Promise.all(promises);
    console.log(results)
    break;
  }
}
