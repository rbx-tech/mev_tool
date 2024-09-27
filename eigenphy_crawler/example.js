// collection bundles
const bundle = {
  _id: "0x07fde7cd31b989193d60f3ac8f44035a9855271b0bf58df2836de9b196fa1039", // bundle id
  timestamp: 1722266759,
  blockNumber: 20431521,
  revenueUsd: 0,
  costUsd: 0,
  profitUsd: 0,
  tippedEth: 0.003891555633105838,
  burnedEth: 0.003081754530080262,
  profitRaws: {
      "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2": 3499605251537621,
      "ETH": -3492956001439914,
      "NET_ETH" : 6649250097707,
      "NET_USDC": 21895,
  },
  builderName: "beaverbuild", // in lower case
  builderAddress: "0x6265617665726275696c642e6f7267",
  types: ["arbitrage"], // "sandwich" ... in lower case,
  tokens: [
    "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
    "0xed89fc0f41d8be2c98b13b7e3cd3e876d73f1d30",
  ],
  pools: ["0x41f11282fb5330700a6c8a67dd2c7ebb9b8adfa5"],
  useFlashloan: false, // optional
  txs: [
      "0x410c53e1ab774756802145a163a3dde8f6cc35850b34d8c333fc78d8ea2644ea",
      "0xde78d61955692ab07d7cca2596a6bfe3d7afaa4f067ac0f653cfd37891db7147"
  ],
  signalTxs: [ // Victim txs, null if cannot detected
    "0x410c53e1ab774756802145a163a3dde8f6cc35850b34d8c333fc78d8ea2644ea"
  ],
  searcherTxs: [
      "0xde78d61955692ab07d7cca2596a6bfe3d7afaa4f067ac0f653cfd37891db7147"
  ],
  source: "libmev", // or eigenphy,
  rawData: { /*... raw data from source */ }
}

// collection pools
const pool = {
  _id: "0x41f11282fb5330700a6c8a67dd2c7ebb9b8adfa5",
  protocol: "Uniswap V2",
  symbol: "UNI-V2",
  tokens: [
      "0xbeef698bd78139829e540622d5863e723e8715f1",
      "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
  ],
  name: "Uniswap V2:BEEF/WETH"
}

// collection tokens
const token = {
  _id: "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
  symbol: "WETH",
  decimals: 18
}

// collection txs
const txDetail = {
  _id: "0x410c53e1ab774756802145a163a3dde8f6cc35850b34d8c333fc78d8ea2644ea",
  bundleId: "0x07fde7cd31b989193d60f3ac8f44035a9855271b0bf58df2836de9b196fa1039",
  blockNumber: 20431521,
  blockHash: "0xcb0c5940e176fb21ddb7bd0b56838eb155a3e2347e9f14bf66d7cc2d647cc3fd",
  from: "0x4d8b18f25Be24F19E9Af37DfeF0d2941066f3a17",
  to: "0x7a250d5630b4cf539739df2c5dacb4c659f2488d",
  value: 649652676586461,
  input: "0x7ff36ab500000000000000000000000000000000000000000000041cc2a3a46e25f000000000000000000000000000000000000000000000000000000000000000000080000000000000000000000000acf244c08a1a41a54a5fb967fdd81fcd34b4c2d00000000000000000000000000000000000000000000000000000000066a7b8080000000000000000000000000000000000000000000000000000000000000002000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc2000000000000000000000000b8baa0e4287890a5f79863ab62b7f175cecbd433",
  transactionIndex: 6,
  gas: "0x7a120",
  gasPrice: "0x37dd52ccf",
  maxFeePerGas: "0x37dd52ccf",
  maxPriorityFeePerGas: "0x347880b40",
  nonce: "0x22b1",
  type: "0x2",
  accessList: [],
  chainId: "0x1",
  v: "0x1",
  r: "0x24be8ce477b8f2dec91ea621498fec35054044116887866f8568bc7494d16502",
  s: "0x60971aa6cdc5ce1c788cb95c184b96bad5564c6c84240d746d0845bfb844730a",
  yParity: "0x1",

  contractName: "UniswapV2Router02", // Put contract addr if cannot detect their name
  tag: "victim", // or mev
  protocols: ["Uniswap V2"],
  inputDecoded: { // Null if cannot decode
      func: "swapExactETHForTokens",
      args: [
          "19420000000000000000000",
          [
              "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
              "0xB8BAa0e4287890a5F79863aB62b7F175ceCbD433"
          ],
          "0xACf244C08a1A41a54a5fB967FDd81FcD34b4C2d0",
          1722267656,
      ]
  },
}
