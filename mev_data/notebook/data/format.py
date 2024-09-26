import json
from datetime import datetime

def read_json(file):
    with open(file, 'r') as f:
        return json.load(f)
    
def write_json(file, data):
    with open(file, 'w') as f:
        json.dump(data, f, indent=4)

def format():
    rates = read_json('rate_eth_usd.json')
    result = {}

    for r in rates:
        date_obj = datetime.strptime(r['timeOpen'], "%Y-%m-%dT%H:%M:%S.%fZ")
        formatted_date = date_obj.strftime("%Y-%m")
        result[formatted_date] = r['quote']['open']
    
    write_json('data.json', result)

if __name__ == '__main__':
    format()
        