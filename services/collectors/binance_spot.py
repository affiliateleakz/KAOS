"""KAOS research-only public Binance spot candle collector; never executes trades."""
import argparse, json, os
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE='https://api.binance.com/api/v3/klines'
INTERVALS={'1m','3m','5m','15m','30m','1h','4h','1d'}

def fetch(symbol, interval='1m', opener=urlopen):
    if not symbol.isalnum() or symbol.upper()!=symbol or len(symbol)>24 or interval not in INTERVALS:
        raise ValueError('Invalid symbol or interval')
    url=BASE+'?'+urlencode({'symbol':symbol,'interval':interval,'limit':100})
    with opener(Request(url,headers={'User-Agent':'KAOS-Research/3.0'}),timeout=20) as response:
        data=json.load(response)
    if not isinstance(data,list): raise ValueError('Unexpected provider response')
    return [{'close_ms':int(c[6]),'close':float(c[4])} for c in data if isinstance(c,list) and len(c)>6],url

def observe(symbol,candles,url,now=None):
    now=now or datetime.now(timezone.utc)
    ms=int(now.timestamp()*1000)
    closed=[c for c in candles if c['close_ms']<ms]
    if len(closed)<21 or not 0<=ms-closed[-1]['close_ms']<=180000: return None
    prices=[c['close'] for c in closed]
    if any(p<=0 for p in prices[-21:]): return None
    average=sum(prices[-20:])/20
    change=prices[-1]/prices[-6]-1
    direction='bullish' if prices[-1]>average and change>.002 else 'bearish' if prices[-1]<average and change<-.002 else 'neutral'
    stamp=datetime.fromtimestamp(closed[-1]['close_ms']/1000,timezone.utc).isoformat()
    return {'asset':symbol,'asset_class':'crypto','source':'technical','direction':direction,
            'strength':round(min(1.,abs(change)*30),4),
            'event_id':f"binance-spot:{symbol}:{closed[-1]['close_ms']}",
            'observed_at':stamp,'published_at':stamp,'source_url':url,
            'summary':f'Binance spot 1m: close {prices[-1]:.8g}; SMA20 {average:.8g}; five-bar change {change:.2%}. Research only.'}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--symbols',default='BTCUSDT,ETHUSDT,SOLUSDT')
    parser.add_argument('--api',default=os.getenv('KAOS_API_BASE',''))
    parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args()
    symbols=[x.strip().upper() for x in args.symbols.split(',') if x.strip()]
    if len(symbols)>150: parser.error('Maximum 150 symbols')
    observations=[]
    for symbol in symbols:
        try:
            candles,url=fetch(symbol)
            item=observe(symbol,candles,url)
            if item: observations.append(item)
        except Exception as exc: print(f'{symbol}: {exc}')
    if args.dry_run:
        print(json.dumps({'mode':'dry_run','observations':observations},indent=2));return
    key=os.getenv('KAOS_COLLECTOR_KEY','')
    if not key or not args.api: parser.error('KAOS_COLLECTOR_KEY and --api required')
    request=Request(args.api.rstrip('/')+'/api/v1/intelligence/ingest',data=json.dumps(observations).encode(),
                    headers={'Content-Type':'application/json','X-KAOS-Collector-Key':key},method='POST')
    with urlopen(request,timeout=25) as response: print(response.read().decode())
if __name__=='__main__': main()
