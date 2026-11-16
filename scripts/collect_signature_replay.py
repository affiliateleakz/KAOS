"""Bounded public Coinbase trade download -> observed five-second bars, without filling gaps."""
import argparse
import json
import time
from datetime import datetime
from pathlib import Path
import httpx


def collect(symbol,pages):
    trades={};cursor=None
    with httpx.Client(timeout=15,headers={'User-Agent':'KAOS-strategy-research/1.0'}) as client:
        for _ in range(pages):
            params={'limit':1000}
            if cursor:params['after']=cursor
            r=client.get('https://api.exchange.coinbase.com/products/'+symbol+'/trades',params=params);r.raise_for_status();rows=r.json()
            if not isinstance(rows,list) or not rows:break
            for row in rows:trades[row['trade_id']]=row
            next_cursor=r.headers.get('cb-after')
            if not next_cursor or next_cursor==cursor:break
            cursor=next_cursor;time.sleep(.4)
    ticks=sorted(trades.values(),key=lambda r:(r['time'],r['trade_id']));groups={}
    for row in ticks:
        ts=int(datetime.fromisoformat(row['time'].replace('Z','+00:00')).timestamp()*1000);bucket=ts//5000*5000
        price=float(row['price']);bar=groups.setdefault(bucket,{'ts':bucket,'open':price,'high':price,'low':price,'close':price})
        bar['high']=max(bar['high'],price);bar['low']=min(bar['low'],price);bar['close']=price
    # First and last buckets may be truncated by the pagination window.
    bars=[bar for ts,bar in sorted(groups.items()) if ts not in (min(groups),max(groups))] if groups else []
    return {'markets':{symbol:bars},'source':'Coinbase Exchange public trades; observed 5-second OHLC, no gap filling','trades_downloaded':len(trades),'requested_pages':pages}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--symbol',default='SOL-USD',choices=['SOL-USD','BTC-USD','ETH-USD']);p.add_argument('--pages',type=int,default=8);p.add_argument('--out',required=True);a=p.parse_args()
    if not 1<=a.pages<=60:p.error('Use 1–60 bounded pages')
    data=collect(a.symbol,a.pages);Path(a.out).write_text(json.dumps(data,separators=(',',':'))+'\n');print({'trades':data['trades_downloaded'],'candles':len(data['markets'][a.symbol])})
