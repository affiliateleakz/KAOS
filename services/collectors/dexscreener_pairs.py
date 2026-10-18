"""Research-only DEX liquidity and volume observations using public DexScreener search."""
import argparse
import json
import math
import os
import time
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ENDPOINT = 'https://api.dexscreener.com/latest/dex/search'

def fetch(query, opener=urlopen):
    if not query or len(query)>80: raise ValueError('Invalid query')
    url=ENDPOINT+'?'+urlencode({'q':query})
    with opener(Request(url,headers={'User-Agent':'KAOS-Research/3.0'}),timeout=20) as response:
        data=json.load(response)
    if not isinstance(data,dict) or not isinstance(data.get('pairs'),list):
        raise ValueError('Unexpected DexScreener response')
    return data['pairs'],url

def number(value):
    try:
        n=float(value)
        return n if math.isfinite(n) and n>=0 else 0.
    except (TypeError,ValueError,OverflowError): return 0.

def observe(pairs, source_url, now=None, min_liquidity=25000, max_pairs=30):
    """Generate neutral market-activity observations, never buy/sell signals."""
    now=now or datetime.now(timezone.utc)
    timestamp=now.isoformat()
    results=[]
    seen=set()
    for pair in pairs:
        if not isinstance(pair,dict): continue
        chain=str(pair.get('chainId',''))[:32]
        address=str(pair.get('pairAddress',''))[:160]
        if not chain or not address or (chain,address) in seen: continue
        seen.add((chain,address))
        liquidity=number((pair.get('liquidity') or {}).get('usd'))
        if liquidity<min_liquidity: continue
        volume=number((pair.get('volume') or {}).get('h24'))
        ratio=volume/liquidity if liquidity else 0
        base=pair.get('baseToken') or {}
        symbol=str(base.get('symbol') or 'UNKNOWN')[:24]
        # Descriptive liquidity activity, not predictive direction.
        strength=min(1.,ratio/5)
        pair_url=pair.get('url')
        if not isinstance(pair_url,str) or not pair_url.startswith('https://dexscreener.com/'):
            pair_url=source_url
        results.append({'asset':f'{chain}:{address}','asset_class':'dex',
            'source':'liquidity','direction':'neutral','strength':round(strength,4),
            'event_id':f'dexscreener:{chain}:{address}:{int(now.timestamp()//300)}',
            'observed_at':timestamp,'published_at':timestamp,'source_url':pair_url,
            'summary':f'{symbol} on {chain}: reported liquidity ${liquidity:,.0f}; 24h volume ${volume:,.0f}; volume/liquidity {ratio:.2f}. Provider snapshot, not a trade recommendation.'})
        if len(results)>=max_pairs: break
    return results

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--queries',default='SOL,ETH,BTC')
    parser.add_argument('--api',default=os.getenv('KAOS_API_BASE',''))
    parser.add_argument('--min-liquidity',type=float,default=25000)
    parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args()
    queries=[q.strip() for q in args.queries.split(',') if q.strip()]
    if not queries or len(queries)>20: parser.error('Provide 1-20 search queries')
    observations=[]
    for query in queries:
        try:
            pairs,url=fetch(query)
            observations.extend(observe(pairs,url,min_liquidity=args.min_liquidity))
        except Exception as exc: print(f'{query}: {exc}',flush=True)
        time.sleep(.3)
    # Deduplicate across overlapping search terms.
    observations=list({o['event_id']:o for o in observations}.values())
    if args.dry_run:
        print(json.dumps({'mode':'dry_run','observations':observations},indent=2));return
    key=os.getenv('KAOS_COLLECTOR_KEY','')
    if not key or not args.api: parser.error('KAOS_COLLECTOR_KEY and --api required')
    request=Request(args.api.rstrip('/')+'/api/v1/intelligence/ingest',
        data=json.dumps(observations[:250]).encode(),
        headers={'Content-Type':'application/json','X-KAOS-Collector-Key':key},method='POST')
    with urlopen(request,timeout=25) as response: print(response.read().decode())
if __name__=='__main__': main()
