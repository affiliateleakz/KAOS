"""KAOS stock market heat map, sourced from Alpaca market-data snapshots.

IEX covers a subset of exchange activity; SIP access requires appropriate rights.
No generated prices, orders or simulated quotes.
"""
import os
import re
import math
import httpx
from fastapi import APIRouter, Depends, HTTPException
from auth import get_current_user
from services_trading import get_entitlements

router=APIRouter(prefix="/api/v1/stocks",tags=["stock-heatmap"])
WATCHLIST={
 "Technology":["AAPL","MSFT","NVDA","AMD","AVGO","ORCL","CRM","ADBE"],
 "Communication":["GOOGL","META","NFLX","DIS"],
 "Consumer":["AMZN","TSLA","HD","COST","WMT","MCD"],
 "Finance":["JPM","BAC","GS","MS","V"],
 "Healthcare":["JNJ","UNH","ABBV","LLY","PFE"],
 "Energy":["XOM","CVX","COP"],
 "Industrials":["CAT","BA","GE","UPS"],
 "ETFs":["SPY","QQQ","DIA","IWM","XLK","XLF","XLE"]
}
SYMBOL=re.compile(r"^[A-Z][A-Z0-9.]{0,11}$")
def value(number):
    try:
        parsed=float(number)
        return parsed if math.isfinite(parsed) else None
    except (TypeError,ValueError,OverflowError):return None

def parse_snapshot(symbol,snapshot):
    daily=snapshot.get("dailyBar") or {}
    previous=snapshot.get("prevDailyBar") or {}
    latest=snapshot.get("latestTrade") or {}
    price=value(daily.get("c")) or value(latest.get("p"))
    prev=value(previous.get("c"))
    change=round(100*(price-prev)/prev,3) if price is not None and prev is not None and prev>0 else None
    return {"symbol":symbol,"price":price,"previous_close":prev,"change_pct":change,
            "volume":value(daily.get("v")),"data_time":daily.get("t") or latest.get("t"),
            "source":"Alpaca","delayed_or_partial":True}

async def require_scanners(user=Depends(get_current_user)):
    if not (await get_entitlements(user)).get("scanners"):
        raise HTTPException(403,"Stock heat map requires scanner access")
    return user

@router.get("/heatmap")
async def heatmap(user=Depends(require_scanners)):
    key=os.getenv("APCA_API_KEY_ID","")
    secret=os.getenv("APCA_API_SECRET_KEY","")
    if not key or not secret:
        raise HTTPException(503,"Stock feed not configured; Alpaca market data credentials required")
    symbols=list(dict.fromkeys(s for group in WATCHLIST.values() for s in group))
    feed=os.getenv("KAOS_ALPACA_STOCK_FEED","iex").lower()
    if feed not in ("iex","sip"):raise HTTPException(503,"Invalid stock feed configuration")
    try:
        async with httpx.AsyncClient(timeout=15,follow_redirects=False) as client:
            response=await client.get("https://data.alpaca.markets/v2/stocks/snapshots",
               params={"symbols":",".join(symbols),"feed":feed},
               headers={"APCA-API-KEY-ID":key,"APCA-API-SECRET-KEY":secret})
            response.raise_for_status()
            data=response.json()
    except (httpx.HTTPError,ValueError) as exc:
        raise HTTPException(503,"Stock heat map source unavailable") from exc
    snapshots=data.get("snapshots",data) if isinstance(data,dict) else {}
    if not isinstance(snapshots,dict):raise HTTPException(503,"Invalid stock provider response")
    sectors=[]
    for sector,tickers in WATCHLIST.items():
        stocks=[parse_snapshot(symbol,snapshots[symbol]) for symbol in tickers
                if isinstance(snapshots.get(symbol),dict)]
        sectors.append({"sector":sector,"stocks":stocks})
    return {"sectors":sectors,"provider":"Alpaca","feed":feed,"research_only":True,
       "execution_enabled":False,"complete_us_market":False,
       "disclaimer":"Curated US stock/ETF watchlist, not the entire market. IEX data is not consolidated SIP coverage. Snapshots may be delayed or unavailable."}
