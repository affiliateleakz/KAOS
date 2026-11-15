"""KAOS read-only DEX market lookup. No trading or token safety endorsement."""
import asyncio
import os
import re
import time
from math import isfinite
from urllib.parse import quote
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from auth import get_current_user
from services_trading import get_entitlements

router=APIRouter(prefix="/api/v1/crypto",tags=["crypto-intelligence"])
DEX_HOST="https://api.dexscreener.com"
ALLOWED_CHAINS={"solana","ethereum","base","bsc","arbitrum","polygon"}
SYMBOL=re.compile(r"^[a-zA-Z0-9 ._:/-]{2,55}$")
ADDRESS=re.compile(r"^[A-Za-z0-9]{20,64}$")

async def require_scanner(user=Depends(get_current_user)):
    if not (await get_entitlements(user)).get("scanners"):
        raise HTTPException(403,"Crypto scanner requires scanner access")
    return user

def numeric(x):
    try:
        v=float(x)
        return v if isfinite(v) else None
    except (ValueError,TypeError,OverflowError):return None

def pair_card(pair):
    base=pair.get("baseToken") or {}
    liquidity=pair.get("liquidity") or {}
    volume=pair.get("volume") or {}
    delta=pair.get("priceChange") or {}
    txns=pair.get("txns") or {}
    pair_url=pair.get("url","")
    if not (isinstance(pair_url,str) and pair_url.startswith("https://dexscreener.com/")):
        pair_url=None
    return {"chain":str(pair.get("chainId") or ""),"dex":str(pair.get("dexId") or ""),
        "pair_address":str(pair.get("pairAddress") or ""),"token_address":str(base.get("address") or ""),
        "symbol":str(base.get("symbol") or "")[:32],"name":str(base.get("name") or "")[:100],
        "price_usd":numeric(pair.get("priceUsd")),"liquidity_usd":numeric(liquidity.get("usd")),
        "volume_24h":numeric(volume.get("h24")),"change_24h":numeric(delta.get("h24")),
        "change_1h":numeric(delta.get("h1")),"market_cap":numeric(pair.get("marketCap")),
        "fdv":numeric(pair.get("fdv")),"buys_24h":(txns.get("h24") or {}).get("buys"),
        "sells_24h":(txns.get("h24") or {}).get("sells"),
        "url":pair_url,"source":"DEX Screener","verified_safe":False}

COINGECKO="https://api.coingecko.com/api/v3"
COINBASE="https://api.exchange.coinbase.com"
# Coinbase fallback universe: liquid USD pairs that need no key or account.
COINBASE_MAJORS=("BTC","ETH","SOL","XRP","ADA","DOGE","AVAX","LINK","DOT","MATIC","LTC","BCH","UNI","ATOM","XLM","ETC","FIL","APT","ARB","OP","SUI","NEAR","INJ","AAVE","MKR","GRT","SAND","MANA","CRV","COMP")
# The bubble map is market-wide, so one cached snapshot serves every member and
# keeps the free endpoints inside their published rate limits.
_MARKET_CACHE={"at":0.0,"payload":None,"provider":None}
_MARKET_TTL=90.0
_MARKET_STALE=600.0


def _coin_row(raw):
    return {"symbol":str(raw.get("symbol") or "").upper()[:12],
            "name":str(raw.get("name") or "")[:60],
            "price_usd":numeric(raw.get("current_price")),
            "market_cap":numeric(raw.get("market_cap")),
            "volume_24h":numeric(raw.get("total_volume")),
            "change_1h":numeric(raw.get("price_change_percentage_1h_in_currency")),
            "change_24h":numeric(raw.get("price_change_percentage_24h_in_currency") or raw.get("price_change_percentage_24h")),
            "change_7d":numeric(raw.get("price_change_percentage_7d_in_currency")),
            "image":raw.get("image") if isinstance(raw.get("image"),str) and raw["image"].startswith("https://") else None,
            "url":"https://www.coingecko.com/en/coins/"+quote(str(raw.get("id") or ""),safe=""),
            "source":"CoinGecko"}


async def _coingecko_market(limit):
    params={"vs_currency":"usd","order":"market_cap_desc","per_page":limit,"page":1,
            "price_change_percentage":"1h,24h,7d","sparkline":"false"}
    async with httpx.AsyncClient(timeout=15,follow_redirects=False) as client:
        response=await client.get(COINGECKO+"/coins/markets",params=params,
                                  headers={"Accept":"application/json","User-Agent":"KAOSTrading-Research/1.0"})
        response.raise_for_status()
        rows=[_coin_row(c) for c in response.json() if isinstance(c,dict)]
    rows=[r for r in rows if r["price_usd"] is not None and r["symbol"]]
    if not rows: raise ValueError("Empty CoinGecko response")
    return rows


async def _coinbase_market(limit, semaphore):
    async def one(client,symbol):
        async with semaphore:
            try:
                response=await client.get(f"{COINBASE}/products/{symbol}-USD/stats",
                                          headers={"Accept":"application/json","User-Agent":"KAOSTrading-Research/1.0"})
                if response.status_code!=200: return None
                data=response.json()
                last=numeric(data.get("last")); open_=numeric(data.get("open")); volume=numeric(data.get("volume"))
            except (httpx.HTTPError,ValueError):
                return None
        if last is None or open_ in (None,0): return None
        return {"symbol":symbol,"name":symbol,"price_usd":last,"market_cap":None,
                "volume_24h":(volume*last) if volume is not None else None,
                "change_1h":None,"change_7d":None,
                "change_24h":round(100*(last-open_)/open_,3),
                "image":None,"url":f"https://www.coinbase.com/price/{symbol.lower()}","source":"Coinbase"}
    async with httpx.AsyncClient(timeout=15,follow_redirects=False,
                                 limits=httpx.Limits(max_connections=6,max_keepalive_connections=6)) as client:
        rows=await asyncio.gather(*(one(client,s) for s in COINBASE_MAJORS[:limit]))
    rows=[r for r in rows if r]
    if not rows: raise ValueError("Empty Coinbase response")
    return rows


@router.get("/market")
async def crypto_market(limit:int=Query(60,ge=10,le=100),user=Depends(require_scanner)):
    """Market-wide bubble map data. Keyless: CoinGecko, then Coinbase as fallback."""
    now=time.monotonic()
    cache=_MARKET_CACHE
    if cache["payload"] and now-cache["at"]<_MARKET_TTL:
        return {**cache["payload"],"cached":True}
    rows,provider,failures=None,None,[]
    try:
        rows=await _coingecko_market(limit); provider="CoinGecko (free, no key)"
    except Exception:
        failures.append("coingecko")
    if not rows:
        try:
            rows=await _coinbase_market(limit,asyncio.Semaphore(6)); provider="Coinbase Exchange public stats (free, no key)"
        except Exception:
            failures.append("coinbase")
    if not rows:
        # Serve a recent snapshot rather than an empty page during a provider hiccup.
        if cache["payload"] and now-cache["at"]<_MARKET_STALE:
            return {**cache["payload"],"cached":True,"stale":True}
        raise HTTPException(503,"Crypto market data unavailable from free providers")
    payload={"coins":rows[:limit],"count":min(len(rows),limit),"provider":provider,
             "weighting":"market_cap" if provider.startswith("CoinGecko") else "24h_volume",
             "failures":failures,"research_only":True,"trade_execution_enabled":False,
             "warning":"Bubble size is a liquidity or market-cap measure, not a recommendation. Prices can be manipulated."}
    _MARKET_CACHE.update(at=now,payload=payload,provider=provider)
    return {**payload,"cached":False}


async def dex_get(path):
    # Route is selected from fixed internal paths, never a user-supplied URL.
    headers={"Accept":"application/json","User-Agent":"KAOSTrading-Research/1.0"}
    try:
        async with httpx.AsyncClient(timeout=12,follow_redirects=False) as client:
            response=await client.get(DEX_HOST+path,headers=headers)
            response.raise_for_status()
            return response.json()
    except (httpx.HTTPError,ValueError) as exc:
        raise HTTPException(503,"DEX Screener market data unavailable") from exc

@router.get("/pairs")
async def find_crypto_pairs(q:str=Query(min_length=2,max_length=55),chain:str|None=None,
                            user=Depends(require_scanner)):
    if not SYMBOL.fullmatch(q) or "://" in q:raise HTTPException(422,"Invalid token search")
    if chain and chain not in ALLOWED_CHAINS:raise HTTPException(422,"Unsupported chain")
    raw=await dex_get("/latest/dex/search?q="+quote(q,safe=""))
    results=[pair_card(p) for p in (raw.get("pairs") or []) if isinstance(p,dict)]
    if chain:results=[p for p in results if p["chain"]==chain]
    return {"pairs":results[:60],"count":min(len(results),60),"provider":"DEX Screener",
       "research_only":True,"trade_execution_enabled":False,"warning":"Prices and liquidity can be manipulated; not a token safety or trading signal."}

@router.get("/token/{chain}/{address}")
async def token_pools(chain:str,address:str,user=Depends(require_scanner)):
    if chain not in ALLOWED_CHAINS or not ADDRESS.fullmatch(address):
        raise HTTPException(422,"Invalid chain or token address")
    raw=await dex_get("/token-pairs/v1/"+chain+"/"+address)
    results=[pair_card(p) for p in raw if isinstance(p,dict)] if isinstance(raw,list) else []
    return {"pairs":results[:60],"provider":"DEX Screener","research_only":True}
