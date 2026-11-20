"""Authenticated, idempotent KAOS historical candle ingestion.

Separate from brokerage trading and member-facing market history. A supervised
worker can POST completed candles repeatedly; Mongo's deterministic _id
prevents duplicate stored bars after restarts.
"""
import os
import re
from datetime import datetime,timezone
from math import isfinite
from secrets import compare_digest
from fastapi import APIRouter,Header,HTTPException
from pydantic import BaseModel,Field
from db import db

router=APIRouter(prefix="/api/v1/collector/candles",tags=["research-candle-recorder"])
SYMBOL=re.compile(r"^[A-Z0-9_.-]{2,32}$")
SOURCES={"coinbase_exchange_public","alpaca_iex","alpaca_sip",
         "oanda_practice_mid","oanda_live_mid"}
INTERVALS={60,300,900}


class RecordedCandle(BaseModel):
    symbol:str=Field(min_length=2,max_length=32)
    asset_class:str
    source:str
    seconds:int
    ts:int
    open:float
    high:float
    low:float
    close:float
    volume:float|None=None


def validate_bars(items,now_ms):
    if not isinstance(items,list) or not 1<=len(items)<=300:
        raise ValueError("Batches must contain 1–300 bars")
    output=[]
    keys=set()
    for row in items:
        bar=row.model_dump() if hasattr(row,"model_dump") else row
        symbol=bar.get("symbol")
        source=bar.get("source")
        seconds=bar.get("seconds")
        asset=bar.get("asset_class")
        ts=bar.get("ts")
        if (not isinstance(symbol,str) or not SYMBOL.fullmatch(symbol)
            or source not in SOURCES or type(seconds) is not int or seconds not in INTERVALS
            or asset not in ("stock","etf","crypto","forex") or type(ts) is not int
            or ts<=0 or ts%(seconds*1000)!=0 or ts+seconds*1000>now_ms):
            raise ValueError("Invalid source, asset, interval, or closed-bar timestamp")
        if source=="coinbase_exchange_public" and asset!="crypto":
            raise ValueError("Coinbase source only supports crypto")
        if source.startswith("alpaca_") and asset not in ("stock","etf"):
            raise ValueError("Alpaca source only supports stocks and ETFs")
        if source.startswith("oanda_") and asset!="forex":
            raise ValueError("OANDA source only supports forex")
        try:
            o,h,l,c=[float(bar[k]) for k in ("open","high","low","close")]
            vol=bar.get("volume")
            v=None if vol is None else float(vol)
        except (KeyError,TypeError,ValueError,OverflowError) as exc:
            raise ValueError("Missing or invalid OHLCV") from exc
        if (not all(isfinite(x) and x>0 for x in (o,h,l,c))
                or l>min(o,c) or h<max(o,c)
                or (v is not None and (not isfinite(v) or v<0))):
            raise ValueError("Invalid OHLCV")
        key=f"{source}:{asset}:{symbol}:{seconds}:{ts}"
        if key in keys:raise ValueError("Duplicate bar in same batch")
        keys.add(key)
        output.append({**bar,"open":o,"high":h,"low":l,"close":c,
                       "volume":v,"_id":key})
    return output


def require_collector(received):
    secret=os.getenv("KAOS_COLLECTOR_KEY","")
    if not secret or not received or not compare_digest(secret,received):
        raise HTTPException(403,"Collector authentication required")


@router.post("/ingest")
async def ingest_completed_candles(items:list[RecordedCandle],
                                   x_kaos_collector_key:str|None=Header(default=None)):
    require_collector(x_kaos_collector_key)
    now_ms=int(datetime.now(timezone.utc).timestamp()*1000)
    try: records=validate_bars(items,now_ms)
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc
    from pymongo import UpdateOne
    # Never overwrite historical price values silently when providers revise
    # a bar: record the existing immutable row instead.
    operations=[UpdateOne({"_id":row["_id"]},{"$setOnInsert":row},upsert=True)
                for row in records]
    result=await db.kaos_research_candles.bulk_write(operations,ordered=False)
    accepted=len(records)
    return {"accepted":accepted,"inserted":result.upserted_count,
            "already_present":accepted-result.upserted_count,
            "research_only":True,"orders_enabled":False}


@router.post("/heartbeat")
async def heartbeat(payload:dict,x_kaos_collector_key:str|None=Header(default=None)):
    require_collector(x_kaos_collector_key)
    worker_id=payload.get("worker_id")
    if not isinstance(worker_id,str) or not re.fullmatch(r"[a-zA-Z0-9_-]{2,48}",worker_id):
        raise HTTPException(422,"Invalid worker ID")
    now=datetime.now(timezone.utc)
    state={"updated_at":now.isoformat(),
           "status":"collecting" if payload.get("status")=="collecting" else "degraded",
           "markets_ok":int(max(0,min(1000,payload.get("markets_ok",0)))),
           "markets_failed":int(max(0,min(1000,payload.get("markets_failed",0)))),
           "last_error_count":int(max(0,min(1000,payload.get("last_error_count",0))))}
    await db.kaos_candle_collector_state.update_one(
        {"_id":worker_id},{"$set":state},upsert=True)
    return {"status":"recorded","research_only":True}
