import {run_crawl_bundles} from './runners/index.js'

async function run() {
    await Promise.all([
        run_crawl_bundles(),
        // run_crawl_signals(),
    ]);
}

run();
