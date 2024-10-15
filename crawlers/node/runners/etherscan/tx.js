import { mongoDb } from "../../mongo.js";
import { Proxy6 } from "../../utils/proxy6.js";
import {sleep} from '../../utils/index.js';
import * as cheerio from 'cheerio';

export async function runEtherscanTxCrawler() {
  while(true) {
    const txs = await mongoDb.transactionsCol.find({etherscan: null}, {_id: 1}).limit(1000).toArray();
    const results = await Promise.all(txs.map((tx) => fetchTxDetail(tx._id)));

    const updates = results.map((it) => {
      const filter = {_id: it.txHash};
      delete it.txHash;
      return {
        updateOne: {
          filter,
          update: {
            $set: { etherscan: it },
          },
        },
      };
    });
    if (updates.length) {
      const result = await mongoDb.transactionsCol.bulkWrite(updates);
      console.log(result);
    }
    await sleep(1000);
  }
}

async function fetchTxDetail(txHash) {
  const url = `https://etherscan.io/tx/${txHash}`;
  try {
    const axios = Proxy6.genNew().toClient();
    const res = await axios.get(url);
    const $ = cheerio.load(res.data);
    const txId = $('#ContentPlaceHolder1_maintable #spanTxHash').text() || '';
    if (!txId.length) {
      throw 'Fetch error!'
    }
    const labels = $('h1.h5.mb-0').parent().next().find('>*').toArray().map((it) => $(it).text().trim());
    // const status = $('i[data-bs-content="The status of the transaction."]').parent().next().text();
    // const timeElm = $('#showUtcLocalDate');
    // const [timestamp, datetimeStr] = [timeElm.attr('data-timestamp'), timeElm.text()];

    const swapsWrapperElm = $('#wrapperContent');
    const aggregateElm = swapsWrapperElm.find('#collapseMoreTxnActionDetails');
    const swaps = [];
    if (!aggregateElm.length) {
      const elems = swapsWrapperElm.find('> div > div.d-flex.flex-wrap.align-items-center');
      swaps.push(...parseActions(elems.toArray()));
    } else {
      const elems = aggregateElm.find('.text-secondary.small.me-1').toArray().map((it) => it.next);
      swaps.push(...parseActions(elems));
    }
    return {
      txHash,
      swaps,
      labels,
      // timestamp,
      // datetimeStr,
    };
  } catch(e) {
    console.log(`Request ${url} failure`, `${e}`.substring(0, 400));
    return null;
  }
}

function parseActions(actionElms) {
  const actions = [];
  for(const line of actionElms) {
    const $ = cheerio.load(line);
    let lineElms = $(line).find('>span').toArray();
    let texts = lineElms.map((it) => $(it).text());
    texts = texts.filter((it) => !['on', 'for'].includes(it.toLowerCase()));

    const prices = [];
    const other = [];
    let index = 0;
    for (const it of texts) {
      if (it.includes('$')) {
        if (index ++ > 3) {
          other.push(null);
        }
        prices.push(Number(it.replace(/[^0-9\.]/g, '')))
      } else {
        other.push(it);
      }
    }
    const poolAddr = $(lineElms[0]).find('a').first().attr('href');
    actions.push({
      type: other[0],
      pool: {
        address: poolAddr ? poolAddr.split('/').at(-1): null,
        protocol: other.at(-1),
      },
      from: {
        amount: other[1],
        token: other[2],
        volumeUsd: prices[0],
      },
      to: {
        amount: other.at(-3),
        token: other.at(-2),
        volumeUsd: prices[1] || null,
      },
    });
  }
  return actions;
}