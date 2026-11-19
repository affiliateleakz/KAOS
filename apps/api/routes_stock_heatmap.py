"""KAOS stock market heat map.

Primary source is authenticated Alpaca market-data snapshots. When Alpaca
credentials are absent (or the call fails in ``auto`` mode) the endpoint falls
back to a keyless public quote preview so the member page is never blank.
Every row is real provider data; nothing is generated or simulated.

IEX covers a subset of exchange activity; SIP access requires appropriate rights.
"""
import asyncio
import math
import os
import re
import time

import httpx
from fastapi import APIRouter, Depends, HTTPException

from auth import get_current_user
from services_trading import get_entitlements

router = APIRouter(prefix="/api/v1/stocks", tags=["stock-heatmap"])
WATCHLIST = {
    "Technology": ["AAPL", "MSFT", "NVDA", "AMD", "AVGO", "ORCL", "CRM", "ADBE"],
    "Communication": ["GOOGL", "META", "NFLX", "DIS"],
    "Consumer": ["AMZN", "TSLA", "HD", "COST", "WMT", "MCD"],
    "Finance": ["JPM", "BAC", "GS", "MS", "V"],
    "Healthcare": ["JNJ", "UNH", "ABBV", "LLY", "PFE"],
    "Energy": ["XOM", "CVX", "COP"],
    "Industrials": ["CAT", "BA", "GE", "UPS"],
    "ETFs": ["SPY", "QQQ", "DIA", "IWM", "XLK", "XLF", "XLE"],
}
SYMBOL = re.compile(r"^[A-Z][A-Z0-9.]{0,11}$")
YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
YAHOO_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
PROVIDERS = ("auto", "alpaca", "yahoo", "off")
# A short cache keeps repeated refreshes from hammering the keyless preview feed.
_YAHOO_CACHE = {"at": 0.0, "rows": None}
_YAHOO_TTL = 60.0


def value(number):
    try:
        parsed = float(number)
        return parsed if math.isfinite(parsed) else None
    except (TypeError, ValueError, OverflowError):
        return None


def parse_snapshot(symbol, snapshot):
    daily = snapshot.get("dailyBar") or {}
    previous = snapshot.get("prevDailyBar") or {}
    latest = snapshot.get("latestTrade") or {}
    price = value(daily.get("c")) or value(latest.get("p"))
    prev = value(previous.get("c"))
    change = round(100 * (price - prev) / prev, 3) if price is not None and prev is not None and prev > 0 else None
    return {"symbol": symbol, "price": price, "previous_close": prev, "change_pct": change,
            "volume": value(daily.get("v")), "data_time": daily.get("t") or latest.get("t"),
            "source": "Alpaca", "delayed_or_partial": True}


def alpaca_configured():
    return bool(os.getenv("APCA_API_KEY_ID", "")) and bool(os.getenv("APCA_API_SECRET_KEY", ""))


def provider_mode():
    mode = os.getenv("KAOS_STOCK_HEATMAP_FALLBACK", "auto").strip().lower() or "auto"
    if mode not in PROVIDERS:
        raise HTTPException(503, "Invalid stock heat map configuration")
    if mode == "alpaca" and not alpaca_configured():
        raise HTTPException(503, "Stock feed not configured; Alpaca market data credentials required")
    if mode == "off" and not alpaca_configured():
        raise HTTPException(503, "Stock feed not configured; Alpaca market data credentials required")
    return mode


async def alpaca_rows(symbols):
    key = os.getenv("APCA_API_KEY_ID", "")
    secret = os.getenv("APCA_API_SECRET_KEY", "")
    if not key or not secret:
        raise ValueError("Alpaca credentials missing")
    feed = os.getenv("KAOS_ALPACA_STOCK_FEED", "iex").lower()
    if feed not in ("iex", "sip"):
        raise ValueError("Invalid stock feed configuration")
    async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
        response = await client.get("https://data.alpaca.markets/v2/stocks/snapshots",
                                    params={"symbols": ",".join(symbols), "feed": feed},
                                    headers={"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret})
        response.raise_for_status()
        data = response.json()
    snapshots = data.get("snapshots", data) if isinstance(data, dict) else {}
    if not isinstance(snapshots, dict):
        raise ValueError("Invalid stock provider response")
    return {symbol: parse_snapshot(symbol, snapshots[symbol])
            for symbol in symbols if isinstance(snapshots.get(symbol), dict)}


async def yahoo_quote(client, semaphore, symbol):
    async with semaphore:
        try:
            response = await client.get(YAHOO_CHART.format(symbol=symbol),
                                        params={"range": "5d", "interval": "1d"},
                                        headers={"User-Agent": YAHOO_UA})
            response.raise_for_status()
            meta = response.json()["chart"]["result"][0]["meta"]
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError):
            return None
    price = value(meta.get("regularMarketPrice"))
    prev = value(meta.get("chartPreviousClose")) or value(meta.get("previousClose"))
    change = round(100 * (price - prev) / prev, 3) if price is not None and prev and prev > 0 else None
    return {"symbol": symbol, "price": price, "previous_close": prev, "change_pct": change,
            "volume": value(meta.get("regularMarketVolume")),
            "data_time": meta.get("regularMarketTime"),
            "source": "Yahoo Finance", "delayed_or_partial": True}


async def yahoo_rows(symbols):
    cached = _YAHOO_CACHE
    if cached["rows"] and (time.monotonic() - cached["at"]) < _YAHOO_TTL:
        rows = cached["rows"]
        return {symbol: rows[symbol] for symbol in symbols if symbol in rows}
    semaphore = asyncio.Semaphore(6)
    # One shared client keeps the keyless preview within polite connection limits.
    async with httpx.AsyncClient(timeout=10, follow_redirects=False,
                                 limits=httpx.Limits(max_connections=6, max_keepalive_connections=6)) as client:
        results = await asyncio.gather(*(yahoo_quote(client, semaphore, symbol) for symbol in symbols))
    rows = {}
    for result in results:
        if not result or not SYMBOL.fullmatch(result["symbol"]):
            continue
        if result["price"] is None:
            continue
        rows[result["symbol"]] = result
    if rows:
        _YAHOO_CACHE.update(at=time.monotonic(), rows=rows)
    return rows


async def require_scanners(user=Depends(get_current_user)):
    if not (await get_entitlements(user)).get("scanners"):
        raise HTTPException(403, "Stock heat map requires scanner access")
    return user


@router.get("/heatmap")
async def heatmap(user=Depends(require_scanners)):
    mode = provider_mode()
    symbols = list(dict.fromkeys(s for group in WATCHLIST.values() for s in group))
    provider = "alpaca" if alpaca_configured() and mode in ("auto", "alpaca") else "yahoo"
    rows, failures = {}, []
    if provider == "alpaca":
        try:
            rows = await alpaca_rows(symbols)
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            failures.append("alpaca")
            if mode != "auto":
                raise HTTPException(503, "Stock heat map source unavailable") from exc
    if provider == "yahoo" or (mode == "auto" and not rows):
        provider = "yahoo"
        try:
            rows = await yahoo_rows(symbols)
        except (httpx.HTTPError, ValueError) as exc:
            raise HTTPException(503, "Stock heat map source unavailable") from exc
    if not rows:
        raise HTTPException(503, "Stock heat map source unavailable")
    sectors = []
    for sector, tickers in WATCHLIST.items():
        stocks = [rows[symbol] for symbol in tickers if symbol in rows]
        sectors.append({"sector": sector, "stocks": stocks})
    if provider == "alpaca":
        meta = {"provider": "Alpaca", "feed": os.getenv("KAOS_ALPACA_STOCK_FEED", "iex").lower(),
                "disclaimer": "Curated US stock/ETF watchlist, not the entire market. IEX data is not "
                              "consolidated SIP coverage. Snapshots may be delayed or unavailable."}
    else:
        meta = {"provider": "Yahoo Finance (unofficial preview)", "feed": "yahoo",
                "disclaimer": "Keyless public quote preview used because Alpaca market-data credentials "
                              "are not configured. Unofficial endpoint, may be delayed, rate limited or "
                              "unavailable, and not licensed for commercial redistribution. Add "
                              "APCA_API_KEY_ID/APCA_API_SECRET_KEY for production market data."}
    return {"sectors": sectors, "research_only": True, "execution_enabled": False,
            "complete_us_market": False, "fallback": provider != "alpaca", "failures": failures, **meta}
