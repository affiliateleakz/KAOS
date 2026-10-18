"""Optional READ-ONLY Pocket Option candle collector using Rufus011's external client.
Install the upstream repository separately; this script does not bundle it or trade.
Requires a DEMO PO_SSID environment variable. Never share the SSID.
"""
import argparse, asyncio, json, os, urllib.request

async def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--market',default='EURUSD_otc')
    ap.add_argument('--timeframes',default='60')
    ap.add_argument('--count',type=int,default=200)
    ap.add_argument('--url',default='http://127.0.0.1:8765/kaos-ai/ingest')
    a=ap.parse_args()
    ssid=os.environ.get('PO_SSID')
    if not ssid:raise SystemExit('Set PO_SSID privately to a demo session before running')
    from cmp_server_pocket_option_2026 import AsyncPocketOption
    async with AsyncPocketOption(ssid) as po:
        for tf in [int(x) for x in a.timeframes.split(',')]:
            try:
                candles=await po.candles(a.market,tf,count=a.count)
                body=json.dumps({'market':a.market,'timeframe':tf,'candles':[{'time':c.time,'open':c.open,'high':c.high,'low':c.low,'close':c.close,'volume':c.volume} for c in candles]}).encode()
                req=urllib.request.Request(a.url,data=body,headers={'Content-Type':'application/json'},method='POST')
                with urllib.request.urlopen(req,timeout=20) as r:print(r.read().decode())
            except Exception as e:print(f'{a.market} {tf}s: {type(e).__name__}: {e}')
if __name__=='__main__':asyncio.run(main())
