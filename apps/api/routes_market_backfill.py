"""Automatic, bounded historical candle retrieval for authenticated KAOS searches.

Official feed adapters only: Coinbase public (crypto), Alpaca keys (stocks),
and configured OANDA v20 (forex). Never use tvdatafeed on a member-triggered
request. Historical research only. Source licenses/rights are independent.
"""
import math
import os
import re
from datetime import datetime, timezone
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from auth import get_current_user
from db import db
from services_trading import get_entitlements

router=APIRouter(prefix="/api/v1/research/market-history",tags=["market-backfill"])
STOCK=re.compile(r"^[A-Z][A-Z0-9.]{0,11}$")
CRYPTO=re.compile(r"^[A-Z0-9]{2,10}-[A-Z]{3,5}$")
FOREX=re.compile(r"^[A-Z]{3}_[A-Z]{3}$")
# Last 300 bars only; no unbounded historical scraping.
GRANULARITIES={60,300,900}
MAX_BARS=300


def validate_market(symbol,asset_class,seconds):
    if seconds not in GRANULARITIES:
        raise ValueError("Only 60, 300, 900 second candles are available")
    if asset_class not in ("stock","etf","crypto","forex"):
        raise ValueError("Unsupported asset class")
    sym=symbol.strip().upper()
    pattern=CRYPTO if asset_class=="crypto" else FOREX if asset_class=="forex" else STOCK
    if not pattern.fullmatch(sym):
        raise ValueError("Invalid market symbol for selected asset class")
    return sym


def normalize_bars(records,*,symbol,asset_class,source,seconds,now_ms):
    """Canonical closed OHLCV, preserving provider IDs without fake continuity."""
    accepted=[]
    for row in records:
        try:
            ts=int(row["ts"])
            o,h,l,c=[float(row[k]) for k in ("open","high","low","close")]
            volume=row.get("volume")
            v=None if volume is None else float(volume)
        except (KeyError,ValueError,TypeError,OverflowError):
            continue
        if (ts<=0 or ts%(seconds*1000)!=0 or ts+seconds*1000>now_ms
                or not all(math.isfinite(x) for x in (o,h,l,c))
                or min(o,h,l,c)<=0 or l>min(o,c) or h<max(o,c)
                or (v is not None and (not math.isfinite(v) or v<0))):
            continue
        accepted.append({"ts":ts,"symbol":symbol,"asset_class":asset_class,
                         "source":source,"seconds":seconds,"open":o,"high":h,
                         "low":l,"close":c,"volume":v})
    accepted.sort(key=lambda x:x["ts"])
    # Deduplicate identical timestamps, reject conflicting provider bars.
    final=[]
    for item in accepted:
        if final and item["ts"]==final[-1]["ts"]:
            if item!=final[-1]:
                raise ValueError("Conflicting source candles at same timestamp")
            continue
        final.append(item)
    gaps=sum(b["ts"]-a["ts"]!=seconds*1000 for a,b in zip(final,final[1:]))
    return final[-MAX_BARS:],gaps


async def fetch_crypto(symbol,seconds):
    from market_data import fetch_crypto_candles, QuoteUnavailable
    try:
        rows=await fetch_crypto_candles(symbol,seconds)
    except QuoteUnavailable as exc:
        raise HTTPException(503,"Coinbase historical data unavailable") from exc
    if not isinstance(rows,list):
        raise HTTPException(502,"Invalid Coinbase history response")
    return ([{"ts":int(item[0])*1000,"open":item[3],"high":item[2],
              "low":item[1],"close":item[4],"volume":item[5]}
             for item in rows if isinstance(item,list) and len(item)==6],
            "coinbase_exchange_public")


async def fetch_stock(symbol,seconds,asset_class):
    key=os.getenv("APCA_API_KEY_ID","")
    secret=os.getenv("APCA_API_SECRET_KEY","")
    if not key or not secret:
        raise HTTPException(503,"Alpaca stock history not configured; admin must connect licensed market-data keys")
    # Single-symbol bounded query. Feed rights determined by the admin's plan.
    timeframe={60:"1Min",300:"5Min",900:"15Min"}[seconds]
    feed=os.getenv("KAOS_ALPACA_DATA_FEED","iex")
    if feed not in ("iex","sip"):
        raise HTTPException(503,"Unsupported Alpaca data feed configuration")
    async with httpx.AsyncClient(timeout=12,follow_redirects=False) as client:
        try:
            response=await client.get(
                f"https://data.alpaca.markets/v2/stocks/{symbol}/bars",
                params={"timeframe":timeframe,"limit":MAX_BARS,"adjustment":"raw",
                        "feed":feed,"sort":"desc"},
                headers={"APCA-API-KEY-ID":key,"APCA-API-SECRET-KEY":secret})
        except httpx.HTTPError as exc:
            raise HTTPException(503,"Alpaca market history unavailable") from exc
    if response.status_code!=200:
        raise HTTPException(503,"Alpaca market history unavailable or feed not entitled")
    payload=response.json()
    raw=payload.get("bars") or []
    if not isinstance(raw,list):
        raise HTTPException(502,"Invalid Alpaca history")
    out=[]
    for b in raw:
        try:
            ts=int(datetime.fromisoformat(b["t"].replace("Z","+00:00")).timestamp()*1000)
            out.append({"ts":ts,"open":b["o"],"high":b["h"],"low":b["l"],
                        "close":b["c"],"volume":b["v"]})
        except (KeyError,ValueError,TypeError,OverflowError):
            continue
    return out,"alpaca_"+feed


async def fetch_forex(symbol,seconds):
    token=os.getenv("KAOS_OANDA_DATA_TOKEN") or ""
    environment=os.getenv("KAOS_OANDA_ENVIRONMENT","practice")
    if not token or environment not in ("practice","live"):
        raise HTTPException(503,"OANDA forex data not configured; admin must connect authorized market-data access")
    base=("https://api-fxpractice.oanda.com" if environment=="practice"
          else "https://api-fxtrade.oanda.com")
    granularity={60:"M1",300:"M5",900:"M15"}[seconds]
    async with httpx.AsyncClient(timeout=12,follow_redirects=False) as client:
        try:
            response=await client.get(f"{base}/v3/instruments/{symbol}/candles",
                params={"count":MAX_BARS,"granularity":granularity,
                        "price":"M"},
                headers={"Authorization":"Bearer "+token,"Accept-Datetime-Format":"RFC3339"})
        except httpx.HTTPError as exc:
            raise HTTPException(503,"OANDA forex history unavailable") from exc
    if response.status_code!=200:
        raise HTTPException(503,"OANDA forex feed unavailable or not entitled")
    raw=response.json().get("candles") or []
    if not isinstance(raw,list):
        raise HTTPException(502,"Invalid OANDA history")
    out=[]
    for b in raw:
        if b.get("complete") is not True:continue
        try:
            mid=b["mid"]
            timestamp=datetime.fromisoformat(b["time"].replace("Z","+00:00"))
            out.append({"ts":int(timestamp.timestamp()*1000),
                        "open":mid["o"],"high":mid["h"],"low":mid["l"],
                        "close":mid["c"],"volume":b.get("volume")})
        except (KeyError,ValueError,TypeError,OverflowError):
            continue
    # OANDA's volume is tick/quote activity, not centralized FX volume.
    return out,"oanda_"+environment+"_mid"


async def guard(user=Depends(get_current_user)):
    if user.get("account_status","active")!="active":
        raise HTTPException(403,"Account is not active")
    return user


@router.get("/search")
async def search(symbol:str=Query(min_length=2,max_length=32),
                 asset_class:str="crypto",seconds:int=60,
                 user=Depends(guard)):
    """One user lookup triggers a cached bounded provider backfill if authorized.

    No implicit futures/PO OTC substitutions. No trading authorization.
    Cached results are isolated research samples and do NOT enter AI training
    archives unless the operator independently approves data rights.
    """
    try: sym=validate_market(symbol,asset_class,seconds)
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc
    import time
    now_ms=int(time.time()*1000)
    cache_key=f"{asset_class}:{sym}:{seconds}"
    row=await db.kaos_market_history_cache.find_one({"_id":cache_key})
    # 5-min caching prevents repeated calls for same market and timeframe.
    if row and row.get("expire_ms",0)>now_ms and row.get("candles"):
        return {**{k:v for k,v in row.items() if k!="_id"},
                "cache_hit":True,"research_only":True}
    # Member-scoped Mongo cooldown across web workers. Cache hits do not
    # consume a request; uncached symbol hopping is rate-limited globally per
    # account so one member cannot exhaust the configured upstream feed.
    from pymongo.errors import DuplicateKeyError
    throttle_id="member:"+str(user["id"])
    try:
        member_lease=await db.kaos_market_history_throttle.find_one_and_update(
            {"_id":throttle_id,"$or":[{"next_ms":{"$lte":now_ms}},
                                      {"next_ms":{"$exists":False}}]},
            {"$set":{"next_ms":now_ms+10000}},
            upsert=True,return_document=True)
    except DuplicateKeyError:
        raise HTTPException(429,"Please allow 10 seconds between new market history requests")
    if member_lease is None:
        raise HTTPException(429,"Please allow 10 seconds between new market history requests")
    # Shared market-key lease prevents duplicate simultaneous upstream fetches.
    if row and row.get("lease_until_ms",0)>now_ms:
        return {"symbol":sym,"asset_class":asset_class,"seconds":seconds,
                "status":"fetch_in_progress","candles":[],"research_only":True}
    from pymongo.errors import DuplicateKeyError
    try:
        locked=await db.kaos_market_history_cache.find_one_and_update(
            {"_id":cache_key,"$or":[{"lease_until_ms":{"$lte":now_ms}},
                                   {"lease_until_ms":{"$exists":False}}]},
            {"$set":{"lease_until_ms":now_ms+25000}},
            upsert=True,return_document=True)
    except DuplicateKeyError:
        return {"symbol":sym,"asset_class":asset_class,"seconds":seconds,
                "status":"fetch_in_progress","candles":[],"research_only":True}
    if locked is None:
        return {"symbol":sym,"asset_class":asset_class,"seconds":seconds,
                "status":"fetch_in_progress","candles":[],"research_only":True}
    try:
        if asset_class=="crypto":
            raw,source=await fetch_crypto(sym,seconds)
        elif asset_class in ("stock","etf"):
            raw,source=await fetch_stock(sym,seconds,asset_class)
        else:
            raw,source=await fetch_forex(sym,seconds)
        bars,gaps=normalize_bars(raw,symbol=sym,asset_class=asset_class,
                                 source=source,seconds=seconds,now_ms=now_ms)
        if not bars:
            raise HTTPException(503,"No completed candles available for this symbol")
        result={"symbol":sym,"asset_class":asset_class,"seconds":seconds,
                "status":"cached_historical_sample","source":source,
                "candles":bars,"bar_count":len(bars),"gaps":gaps,
                "fetched_at_ms":now_ms,"expire_ms":now_ms+300000,
                "research_only":True,"cache_hit":False,
                "ai_training_approved":False,
                "note":"Historical research sample. Feed rights/coverage must be reviewed; gaps not interpolated. Not a live prediction."}
        await db.kaos_market_history_cache.update_one(
            {"_id":cache_key},{"$set":{**result,"lease_until_ms":0}},upsert=True)
        return result
    finally:
        await db.kaos_market_history_cache.update_one(
            {"_id":cache_key,"lease_until_ms":now_ms+25000},
            {"$set":{"lease_until_ms":0}})


@router.get("/assessment")
async def market_assessment(symbol:str=Query(min_length=2,max_length=32),
                            asset_class:str="stock",seconds:int=60,
                            user=Depends(guard)):
    """Fuse bounded cached market candles with existing collected evidence.

    Deliberately doesn't launch a second external fetch; UI first calls /search.
    """
    try:sym=validate_market(symbol,asset_class,seconds)
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc
    from kaos_market_assessment import assess
    from datetime import timedelta
    import time
    now_ms=int(time.time()*1000)
    key=f"{asset_class}:{sym}:{seconds}"
    cached=await db.kaos_market_history_cache.find_one({"_id":key})
    if not cached or not cached.get("candles"):
        raise HTTPException(404,"Search and retrieve this market's historical candles first")
    if cached.get("expire_ms",0)<=now_ms:
        raise HTTPException(409,"Historical research sample is stale; search again")
    cutoff=(datetime.now(timezone.utc)-timedelta(days=7)).isoformat()
    # Research evidence is sourced from the same already-ingested intelligence
    # corpus. Not a live news/social fetch or claim of complete coverage.
    rows=await db.kaos_intelligence.find(
        {"asset":sym,"asset_class":asset_class,"observed_at":{"$gte":cutoff}},
        {"_id":0,"source":1,"direction":1,"event_id":1,"summary":1,
         "observed_at":1,"source_url":1}).sort("observed_at",-1).limit(100).to_list(100)
    try:
        report=assess(cached["candles"],rows,symbol=sym,asset_class=asset_class,
                      seconds=seconds,source=cached["source"],now_ms=now_ms)
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc
    return {**report,"history_cache_hit":True,"news_social_collection":"already_ingested_only",
            "options_chain_checked":False}


@router.get("/options/chain-review")
async def review_options_chain(symbol:str=Query(min_length=1,max_length=12),
                               user=Depends(guard)):
    """Read-only, bounded Tradier listed-options chain research.

    Not a call/put or expiration recommendation. Sandbox quotes are delayed.
    No provider request unless operator configured market-data credentials.
    """
    symbol=symbol.strip().upper()
    if not STOCK.fullmatch(symbol):
        raise HTTPException(422,"Options require a valid stock or ETF underlying")
    token=os.getenv("TRADIER_TOKEN","")
    if not token:
        raise HTTPException(503,"Tradier options market data is not configured")
    sandbox=os.getenv("KAOS_TRADIER_SANDBOX","true").lower()!="false"
    api="https://sandbox.tradier.com/v1" if sandbox else "https://api.tradier.com/v1"
    headers={"Authorization":"Bearer "+token,"Accept":"application/json"}
    async with httpx.AsyncClient(timeout=12,follow_redirects=False) as client:
        try:
            resp=await client.get(api+"/markets/options/expirations",
                                  params={"symbol":symbol,"includeAllRoots":"false"},headers=headers)
            if resp.status_code!=200:
                raise HTTPException(503,"Options expiration feed unavailable or not entitled")
            raw=(resp.json().get("expirations") or {}).get("date") or []
            if isinstance(raw,str):raw=[raw]
            if not isinstance(raw,list):
                raise HTTPException(502,"Invalid expiration response")
            from datetime import date
            today=datetime.now(timezone.utc).date()
            dates=sorted(d for item in raw if isinstance(item,str)
                         for d in [date.fromisoformat(item)]
                         if d>=today)
            if not dates:
                return {"status":"no_listed_expirations","underlying":symbol,
                        "candidates":[],"call_put_recommendation":"NONE",
                        "recommended_expiration":None,"research_only":True}
            # Query at most one nearest listed expiry to bound provider costs.
            expiry=dates[0].isoformat()
            chain=await client.get(api+"/markets/options/chains",
                    params={"symbol":symbol,"expiration":expiry,"greeks":"true"},headers=headers)
        except (httpx.HTTPError,ValueError,KeyError,TypeError) as exc:
            raise HTTPException(503,"Options market data unavailable") from exc
    if chain.status_code!=200:
        raise HTTPException(503,"Options chain unavailable or not entitled")
    raw=(chain.json().get("options") or {}).get("option") or []
    if isinstance(raw,dict):raw=[raw]
    from kaos_options_candidates import screen
    try:
        result=screen(symbol,expiry,raw,sandbox=sandbox)
    except ValueError as exc:
        raise HTTPException(502,str(exc)) from exc
    return {**result,"available_expirations":len(dates),
            "options_chain_checked":True}
