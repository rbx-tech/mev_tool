import {runCrawlEigenphyBundles } from './runners/eigenphy/index.js'
import {crawlLibMevBundles } from './runners/libmev/bundle.js'
import {mongoDb} from './mongo.js'
import { sleep } from './utils/index.js';

async function run() {
    await mongoDb.connect();
    console.log('Connected to database');
    let isEigenphyRunning = false;
    let isLibmevRunning = false;
    while(true) {
        if (!isEigenphyRunning) {
            const [isEnable, nextRun] = await Promise.all([
                mongoDb.getInfo('eigenphy_enable', false), 
                mongoDb.getInfo('eigenphy_next_run', Date.now()),
            ]);
            if (isEnable && nextRun <= Date.now()) {
                isEigenphyRunning = true;
                runCrawlEigenphyBundles().then(() => {
                    isEigenphyRunning = false;
                });
            }
        }
        if (!isLibmevRunning) {
            const [isEnable, nextRun] = await Promise.all([
                mongoDb.getInfo('libmev_enable', false), 
                mongoDb.getInfo('libmev_next_run', Date.now()),
            ]);
            if (isEnable && nextRun <= Date.now()) {
                isLibmevRunning = true;
                crawlLibMevBundles().then(() => {
                    isLibmevRunning = false;
                });
            }
        }
        await sleep(10000);
    }
}

run();
