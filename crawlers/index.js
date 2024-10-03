import {runCrawlBundles, runCrawlSignals} from './runners/index.js'
import {mongoDb} from './mongo.js'

async function run() {
    await mongoDb.connect();
    console.log('Connected to database');
    await Promise.all([
        runCrawlBundles(),
        runCrawlSignals(),
    ]);
    process.exit(0);
}

run();
