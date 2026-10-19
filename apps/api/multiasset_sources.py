"""Read-only OHLCV adapters for authorized Alpaca IEX stocks and OANDA forex."""
import os
from datetime import datetime,timezone
from math import isfinite
import httpx

STOCKS=("SPY","QQQ","AAPL","MSFT","NVDA","TSLA")
FOREX=("EUR_USD","GBP_USD","USD_JPY","AUD_USD")
STOCK_TF={60:"1Min",300:"5Min",900:"15Min"}
FOREX_TF={60:"M1",300:"M5",900:"M15"}

def parsed(t):
    return datetime.fromisoformat(t.replace("Z","+00:00")).astimezone(timezone.utc)

def bar(asset_class,symbol,seconds,ts,prices,vol,source,now):
    row={"asset_class":asset_class,"symbol":symbol,"seconds":seconds,
         "ts":int(parsed(ts).timestamp()*1000),"source":source,"volume":float(vol)}
    row.update({k:float(prices[k]) for k in ("open","high","low","close")})
    p=[row[k] for k in ("open","high","low","close")]
    if not all(isfinite(v) and v>0 for v in p):return None
    if not isfinite(row["volume"]) or row["volume"]<0:return None
    if not row["low"]<=min(row["open"],row["close"])<=max(row["open"],row["close"])<=row["high"]:return None
    if row["ts"]+seconds*1000>int(now.timestamp()*1000):return None
    return row

async def stocks(symbol,seconds):
    if symbol not in STOCKS or seconds not in STOCK_TF:raise ValueError("Unsupported stock")
    key=os.getenv("APCA_API_KEY_ID");secret=os.getenv("APCA_API_SECRET_KEY")
    if not key or not secret:raise RuntimeError("Alpaca keys not configured")
    now=datetime.now(timezone.utc)
    async with httpx.AsyncClient(timeout=15) as client:
        res=await client.get("https://data.alpaca.markets/v2/stocks/"+symbol+"/bars",
            params={"timeframe":STOCK_TF[seconds],"feed":"iex","limit":100,"end":now.isoformat()},
            headers={"APCA-API-KEY-ID":key,"APCA-API-SECRET-KEY":secret})
        res.raise_for_status();rows=res.json()["bars"]
    result=[]
    for x in rows:
        y=bar("stock",symbol,seconds,x["t"],dict(open=x["o"],high=x["h"],low=x["l"],close=x["c"]),x["v"],"alpaca_iex",now)
        if y:result.append(y)
    return result

async def forex(symbol,seconds):
    if symbol not in FOREX or seconds not in FOREX_TF:raise ValueError("Unsupported forex")
    token=os.getenv("OANDA_API_TOKEN")
    if not token:raise RuntimeError("OANDA token not configured")
    now=datetime.now(timezone.utc)
    domain="api-fxtrade.oanda.com" if os.getenv("OANDA_ENV")=="live" else "api-fxpractice.oanda.com"
    async with httpx.AsyncClient(timeout=15) as client:
        res=await client.get("https://"+domain+"/v3/instruments/"+symbol+"/candles",
            params={"granularity":FOREX_TF[seconds],"count":100,"price":"M"},
            headers={"Authorization":"Bearer "+token})
        res.raise_for_status();rows=res.json()["candles"]
    result=[]
    for x in rows:
        if not x.get("complete") or not x.get("mid"):continue
        mid=x["mid"]
        y=bar("forex",symbol,seconds,x["time"],dict(open=mid["o"],high=mid["h"],low=mid["l"],close=mid["c"]),x.get("volume",0),"oanda_mid",now)
        if y:result.append(y)
    return result
