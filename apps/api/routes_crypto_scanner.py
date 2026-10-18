"""KAOS read-only DEX market lookup. No trading or token safety endorsement."""
import os
import re
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
