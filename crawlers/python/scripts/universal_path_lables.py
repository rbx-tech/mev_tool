import os
import re
import sys
import threading

from pymongo import UpdateOne

sys.path.append(os.getcwd())

from src.mongo import MongoDb


def get_query(offset: int, limit: int):
  return [
    {
        '$match': {
            'contractName': re.compile(r"UniversalRouter"), 
            'inputDecoded.func': 'execute'
        }
    }, 
    { '$skip': offset },
    { '$limit': limit },
    {
        '$project': {
            'txHash': '$_id', 
            'inputs': {
                '$map': {
                    'input': {
                        '$filter': {
                            'input': '$inputDecoded.args.inputs', 
                            'as': 'item', 
                            'cond': {
                                '$regexMatch': {
                                    'input': {
                                        '$cond': {
                                            'if': {
                                                '$eq': [
                                                    {
                                                        '$type': '$$item'
                                                    }, 'array'
                                                ]
                                            }, 
                                            'then': {
                                                '$first': '$$item'
                                            }, 
                                            'else': ''
                                        }
                                    }, 
                                    'regex': re.compile(r"SWAP")
                                }
                            }
                        }
                    }, 
                    'as': 'item', 
                    'in': {
                        '$mergeObjects': [
                            {
                                '$arrayElemAt': [
                                    '$$item', 1
                                ]
                            }, {
                                'command': {
                                    '$arrayElemAt': [
                                        '$$item', 0
                                    ]
                                }
                            }
                        ]
                    }
                }
            }
        }
    },
    { '$unwind': '$inputs' }, 
    {
        '$project': {
            'txHash': 1, 
            'input': '$inputs', 
            'protocol': {
                '$cond': {
                    'if': {
                        '$regexMatch': {
                            'input': '$command', 
                            'regex': re.compile(r"V3")
                        }
                    }, 
                    'then': 'UniSwapV2', 
                    'else': 'UniSwapV3'
                }
            }, 
            'paths': {
                '$map': {
                    'input': {
                        '$filter': {
                            'input': '$inputs.path', 
                            'as': 'item', 
                            'cond': {
                                '$eq': [
                                    {
                                        '$type': '$$item'
                                    }, 'string'
                                ]
                            }
                        }
                    }, 
                    'as': 'item', 
                    'in': {
                        '$toLower': '$$item'
                    }
                }
            }
        }
    }, {
        '$project': {
            'protocol': 1, 
            'txHash': 1, 
            'paths': 1, 
            'input': 1, 
            'pairs': {
                '$zip': {
                    'inputs': [
                        '$paths', {
                            '$slice': ['$paths', 1, { '$size': '$paths' }]
                        }
                    ]
                }
            }
        }
    }, 
    {'$unwind': '$pairs'}, 
    {
        '$lookup': {
            'from': 'pools', 
            'let': {
                'pairs': '$pairs', 
                'protocol': '$protocol'
            }, 
            'pipeline': [
                {
                    '$match': {
                        '$expr': {
                            '$and': [
                                {
                                    '$eq': [
                                        '$protocol', '$$protocol'
                                    ]
                                }, {
                                    '$in': [
                                        {
                                            '$arrayElemAt': [
                                                '$tokens', 0
                                            ]
                                        }, '$$pairs'
                                    ]
                                }, {
                                    '$in': [
                                        {
                                            '$arrayElemAt': [
                                                '$tokens', 1
                                            ]
                                        }, '$$pairs'
                                    ]
                                }
                            ]
                        }
                    }
                }
            ], 
            'as': 'pool',
        }
    },
    {'$unwind': '$pool'},
    {'$unset': ['paths', 'pairs']}
  ]
  

is_running = True
  
def runner(mongodb: MongoDb, offset, limit):
  print(f'Start threading offset={offset}')
  global is_running
  results = list(mongodb.transactions.aggregate(get_query(offset, limit)))
  if len(results) == 0:
    is_running = False
    return

  tx_hash = ''
  txt_cnt = 0
  updates = []
  for x in results:
    if x['txHash'] != tx_hash:
      tx_hash = x['txHash']
      txt_cnt = 0

    x['_id'] = f'{tx_hash}_{txt_cnt}'
    updates.append(UpdateOne({'_id': x['_id']}, {'$set': x}, upsert=True))
    txt_cnt += 1

  if len(updates) > 0:
    res = mongodb.universal_analytics.bulk_write(updates)
    print(offset, f'Result offset={offset} limit={limit}: {res}')
  else:
    print(offset, f'No result found offset={offset} limit={limit}!')
  
  
def main():
  global is_running
  mongodb = MongoDb()
  mongodb.connect()

  offset = mongodb.get_info('universal_analytics_offset', 0)
  limit = 50
  
  threads: list[threading.Thread] = []
  
  while is_running:
    for _ in range(0, 15):
      t = threading.Thread(target=runner, args=(mongodb, offset, limit))
      t.start()
      threads.append(t)
      offset += limit

    for t in threads:
      t.join()
    mongodb.set_info('universal_analytics_offset', offset)

main()