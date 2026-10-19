"""Run separately from the web process: python candle_research_worker.py.

Captures actual closed Coinbase OHLCV candles, idempotently. No orders or AI
training are executed here. Worker must remain deployed for continuous capture.
"""
import asyncio
import os
from datetime import datetime,timezone
from math import isfinite
from db import db
from market_data import fetch_crypto_candles, closed_candles
from multiasset_sources import STOCKS, FOREX, stocks, forex

DEFAULT_MARKETS=("BTC-USD","ETH-USD","SOL-USD")
DEFAULT_PERIODS=(60,300,900)

def normalize(rows, symbol,seconds,now):
    closed=closed_candles(rows,seconds,now)
    out=[]
    for c in closed:
        vals=[c[k] for k in ("open","high","low","close","volume")]
        if not all(isfinite(x) for x in vals) or min(vals[:4])<=0 or c["volume"]<0:
            continue
        if not (c["low"]<=min(c["open"],c["close"])<=max(c["open"],c["close"])<=c["high"]):
            continue
        out.append({"symbol":symbol,"seconds":seconds,"ts":c["time"]*1000,
          "asset_class":"crypto","open":c["open"],"high":c["high"],"low":c["low"],
          "close":c["close"],"volume":c["volume"],"source":"coinbase_exchange_public_candles"})
    return out

async def collect_once(markets=DEFAULT_MARKETS, periods=DEFAULT_PERIODS):
    now=datetime.now(timezone.utc)
    collected=0;errors=[]
    for symbol in markets:
        for seconds in periods:
            try:
                raw=await fetch_crypto_candles(symbol,seconds)
                rows=normalize(raw,symbol,seconds,now)
                for row in rows:
                    await db.kaos_research_candles.update_one(
                      {"asset_class":"crypto","symbol":symbol,"seconds":seconds,"ts":row["ts"],"source":row["source"]},
                      {"$setOnInsert":row},upsert=True)
                collected+=len(rows)
            except Exception as exc:
                errors.append({"symbol":symbol,"seconds":seconds,
                               "reason":type(exc).__name__})
    for asset_class, symbols, fetcher in (("stock",STOCKS,stocks),("forex",FOREX,forex)):
        for symbol in symbols:
            for seconds in periods:
                try:
                    rows=await fetcher(symbol,seconds)
                    for row in rows:
                        await db.kaos_research_candles.update_one(
                          {"asset_class":asset_class,"symbol":symbol,"seconds":seconds,
                           "ts":row["ts"],"source":row["source"]},
                          {"$setOnInsert":row},upsert=True)
                    collected+=len(rows)
                except Exception as exc:
                    errors.append({"asset_class":asset_class,"symbol":symbol,
                                   "seconds":seconds,"reason":type(exc).__name__})
    await db.kaos_candle_collector_state.update_one({"_id":"coinbase_worker"},
      {"$set":{"last_run":now.isoformat(),"processed_candles":collected,
               "errors":errors,"mode":"research_only","orders_enabled":False}},upsert=True)
    return collected

async def run():
    if os.getenv("KAOS_ENABLE_CANDLE_WORKER")!="true":
        raise RuntimeError("Set KAOS_ENABLE_CANDLE_WORKER=true to run a dedicated collector")
    await db.kaos_research_candles.create_index(
      [("asset_class",1),("symbol",1),("seconds",1),("ts",1),("source",1)],unique=True)
    while True:
        await collect_once()
        await asyncio.sleep(60)

if __name__=="__main__":
    asyncio.run(run())
