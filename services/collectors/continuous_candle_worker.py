"""Continuously running KAOS candle archive collector, research only.

One independent supervised process on an always-on VPS, NEVER a web request,
extension, order engine or on-demand chat background job. Polls authorized
configured sources, stores completed bars through authenticated KAOS ingest.
"""
import argparse
import json
import os
import re
import signal
import time
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError

API_SOURCE={
    "crypto":"coinbase_exchange_public",
    "stock":"alpaca_iex",
    "etf":"alpaca_iex",
    "forex":"oanda_practice_mid",
}
SUPPORTED={60,300,900}
STOP=False


def stop(*_):
    global STOP
    STOP=True


def validate_config(doc):
    if not isinstance(doc,dict) or not isinstance(doc.get("markets"),list):
        raise ValueError("Expected markets array")
    if not 1<=len(doc["markets"])<=150:
        raise ValueError("Markets list must have 1..150 entries")
    out=[];seen=set()
    for item in doc["markets"]:
        if not isinstance(item,dict):
            raise ValueError("Invalid market entry")
        symbol=item.get("symbol")
        cls=item.get("asset_class")
        seconds=item.get("seconds",60)
        if (not isinstance(symbol,str) or not re.fullmatch(r"[A-Z0-9_.-]{2,32}",symbol)
            or cls not in API_SOURCE or type(seconds) is not int or seconds not in SUPPORTED):
            raise ValueError("Invalid market symbol/class/timeframe")
        if (cls=="crypto" and not re.fullmatch(r"[A-Z0-9]{2,10}-[A-Z]{3,5}",symbol)
            or cls in ("stock","etf") and not re.fullmatch(r"[A-Z][A-Z0-9.]{0,11}",symbol)
            or cls=="forex" and not re.fullmatch(r"[A-Z]{3}_[A-Z]{3}",symbol)):
            raise ValueError("Wrong symbol for asset class")
        k=(cls,symbol,seconds)
        if k in seen:raise ValueError("Duplicate market")
        seen.add(k)
        out.append({"symbol":symbol,"asset_class":cls,"seconds":seconds})
    return out


def request_json(url,*,headers=None,timeout=15):
    req=Request(url,headers={"User-Agent":"KAOS-candle-recorder/1.0",
                             "Accept":"application/json",**(headers or {})})
    with urlopen(req,timeout=timeout) as response:
        return json.load(response)


def retrieve(market, *,provider_fetch=request_json):
    symbol=market["symbol"];cls=market["asset_class"];seconds=market["seconds"]
    if cls=="crypto":
        url="https://api.exchange.coinbase.com/products/"+quote(symbol,safe="")+"/candles?"
        payload=provider_fetch(url+urlencode({"granularity":seconds}))
        if not isinstance(payload,list):raise ValueError("Invalid Coinbase response")
        return ([{"ts":int(row[0])*1000,"low":row[1],"high":row[2],
                  "open":row[3],"close":row[4],"volume":row[5]}
                 for row in payload if isinstance(row,list) and len(row)>=6],
                "coinbase_exchange_public")
    if cls in ("stock","etf"):
        key=os.getenv("APCA_API_KEY_ID");secret=os.getenv("APCA_API_SECRET_KEY")
        if not key or not secret:raise ValueError("Alpaca data credentials unavailable")
        feed=os.getenv("KAOS_ALPACA_DATA_FEED","iex")
        if feed not in ("iex","sip"):raise ValueError("Invalid Alpaca feed configuration")
        url="https://data.alpaca.markets/v2/stocks/"+quote(symbol,safe="")+"/bars?"
        payload=provider_fetch(url+urlencode({"timeframe":{60:"1Min",300:"5Min",900:"15Min"}[seconds],
                             "limit":300,"sort":"desc","adjustment":"raw","feed":feed}),
                             headers={"APCA-API-KEY-ID":key,"APCA-API-SECRET-KEY":secret})
        from datetime import datetime
        bars=(payload.get("bars") or []) if isinstance(payload,dict) else []
        return ([{"ts":int(datetime.fromisoformat(b["t"].replace("Z","+00:00")).timestamp()*1000),
                  "open":b["o"],"high":b["h"],"low":b["l"],
                  "close":b["c"],"volume":b["v"]} for b in bars],
                "alpaca_"+feed)
    token=os.getenv("KAOS_OANDA_DATA_TOKEN")
    env=os.getenv("KAOS_OANDA_ENVIRONMENT","practice")
    if not token or env not in ("practice","live"):
        raise ValueError("OANDA credentials or environment unavailable")
    base="https://api-fxpractice.oanda.com" if env=="practice" else "https://api-fxtrade.oanda.com"
    url=base+"/v3/instruments/"+quote(symbol,safe="")+"/candles?"
    payload=provider_fetch(url+urlencode({"count":300,
            "granularity":{60:"M1",300:"M5",900:"M15"}[seconds],"price":"M"}),
            headers={"Authorization":"Bearer "+token})
    from datetime import datetime
    bars=payload.get("candles") if isinstance(payload,dict) else []
    return ([{"ts":int(datetime.fromisoformat(b["time"].replace("Z","+00:00")).timestamp()*1000),
              "open":b["mid"]["o"],"high":b["mid"]["h"],"low":b["mid"]["l"],
              "close":b["mid"]["c"],"volume":b.get("volume")}
             for b in bars or [] if b.get("complete") is True],
            "oanda_"+env+"_mid")


def prepare_rows(market,records,source,*,now_ms):
    """Do not invent missing candles, alter observed price or include open bars."""
    import math
    out=[];seen=set()
    for row in records:
        ts=int(row["ts"])
        interval=market["seconds"]*1000
        if ts<=0 or ts%interval or ts+interval>now_ms:
            continue
        o,h,l,c=[float(row[k]) for k in ("open","high","low","close")]
        v=None if row.get("volume") is None else float(row["volume"])
        if (not all(math.isfinite(x) and x>0 for x in (o,h,l,c))
                or l>min(o,c) or h<max(o,c)
                or v is not None and (not math.isfinite(v) or v<0)):
            continue
        if ts in seen:continue
        seen.add(ts)
        out.append({**market,"source":source,"ts":ts,
                    "open":o,"high":h,"low":l,"close":c,"volume":v})
    return sorted(out,key=lambda r:r["ts"])


def transmit(url,payload,*,key,timeout=20):
    if not url.startswith("https://") and not url.startswith("http://127.0.0.1:"):
        raise ValueError("Use HTTPS KAOS API (loopback development exception)")
    data=json.dumps(payload,allow_nan=False).encode()
    req=Request(url,data=data,method="POST",
                headers={"Content-Type":"application/json",
                         "X-KAOS-Collector-Key":key,
                         "User-Agent":"KAOS-candle-recorder/1.0"})
    with urlopen(req,timeout=timeout) as response:
        return json.load(response)


def cycle(markets,*,api_base,key,now_ms=None,fetch=retrieve,post=transmit,pause=.5,
          last_seen=None):
    now_ms=now_ms or int(time.time()*1000)
    last_seen=last_seen if last_seen is not None else {}
    ok=0;failed=0;count=0;problems=[]
    for market in markets:
        if STOP:break
        ident=(market["asset_class"],market["symbol"],market["seconds"])
        try:
            fetched,source=fetch(market)
            rows=prepare_rows(market,fetched,source,now_ms=now_ms)
            # Always replay a small overlap so process restarts and delayed
            # closures are recovered. Idempotent ingest handles duplicates.
            if ident in last_seen:
                rows=[r for r in rows if r["ts"]>=last_seen[ident]-market["seconds"]*1000*5]
            if rows:
                # The API refuses bigger batches.
                for i in range(0,len(rows),300):
                    part=rows[i:i+300]
                    answer=post(api_base.rstrip("/")+"/api/v1/collector/candles/ingest",part,key=key)
                    if answer.get("accepted")!=len(part):
                        raise RuntimeError("Archive ingestion did not accept all rows")
                last_seen[ident]=rows[-1]["ts"]
                count+=len(rows)
            ok+=1
        except (ValueError,KeyError,TypeError,HTTPError,URLError,TimeoutError,OSError,RuntimeError) as exc:
            failed+=1
            problems.append({"symbol":market["symbol"],"type":type(exc).__name__})
        if pause:time.sleep(pause)
    return {"markets_ok":ok,"markets_failed":failed,"bars_submitted":count,
            "last_error_count":failed,"issues":problems,"status":"collecting" if not failed else "degraded"}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--config",required=True)
    parser.add_argument("--api",default=os.getenv("KAOS_API_BASE",""))
    parser.add_argument("--interval",type=int,default=300)
    parser.add_argument("--pause",type=float,default=.5)
    parser.add_argument("--worker-id",default="continuous_candles_v1")
    parser.add_argument("--once",action="store_true")
    args=parser.parse_args()
    if not 60<=args.interval<=3600 or not 0<=args.pause<=5:
        parser.error("Interval must be 60..3600, pause must be 0..5 seconds")
    if not re.fullmatch(r"[A-Za-z0-9_-]{2,48}",args.worker_id):
        parser.error("Invalid worker ID")
    key=os.getenv("KAOS_COLLECTOR_KEY")
    if not key or not args.api:
        parser.error("KAOS_COLLECTOR_KEY and KAOS_API_BASE are required")
    markets=validate_config(json.loads(Path(args.config).read_text()))
    signal.signal(signal.SIGTERM,stop)
    signal.signal(signal.SIGINT,stop)
    last_seen={}
    while not STOP:
        beginning=time.monotonic()
        report=cycle(markets,api_base=args.api,key=key,pause=args.pause,last_seen=last_seen)
        try:
            transmit(args.api.rstrip("/")+"/api/v1/collector/candles/heartbeat",
                     {"worker_id":args.worker_id,**report},key=key)
        except (ValueError,OSError,URLError,HTTPError,TimeoutError) as exc:
            report["heartbeat_error"]=type(exc).__name__
        print(json.dumps({"utc":datetime.now(timezone.utc).isoformat(),**report}),flush=True)
        if args.once:break
        remaining=args.interval-(time.monotonic()-beginning)
        if remaining>0:time.sleep(remaining)

if __name__=="__main__":main()
