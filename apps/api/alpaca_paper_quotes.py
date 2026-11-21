"""Time-verified Alpaca stock quotes for paper-order preflight.

Equity IEX quotes are a limited market view and not guaranteed execution
prices. Reject closed market, nonpositive spread or stale timestamps.
"""
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import httpx

DATA_ORIGIN="https://data.alpaca.markets"
MAX_QUOTE_AGE_SECONDS=10


class MarketUnavailable(ValueError):
    pass


def _time(value):
    try:
        result=datetime.fromisoformat(str(value).replace("Z","+00:00"))
        if result.tzinfo is None:
            raise ValueError()
        return result.astimezone(timezone.utc)
    except (ValueError,TypeError) as exc:
        raise MarketUnavailable("Alpaca quote has no verified UTC time") from exc


def parse_stock_quote(symbol,data,*,now=None):
    if now is None:
        now=datetime.now(timezone.utc)
    q=data.get("quote") if isinstance(data,dict) else None
    if not isinstance(q,dict) or data.get("symbol")!=symbol:
        raise MarketUnavailable("Quote symbol mismatch")
    try:
        bid,ask=Decimal(str(q["bp"])),Decimal(str(q["ap"]))
    except (InvalidOperation,KeyError,TypeError) as exc:
        raise MarketUnavailable("Invalid bid/ask") from exc
    if not bid.is_finite() or not ask.is_finite() or bid<=0 or ask<bid:
        raise MarketUnavailable("Invalid quote spread")
    ts=_time(q.get("t"))
    age=(now-ts).total_seconds()
    if age<0 or age>MAX_QUOTE_AGE_SECONDS:
        raise MarketUnavailable("Market quote stale or not yet published")
    return {"symbol":symbol,"bid":format(bid,"f"),"ask":format(ask,"f"),
            "timestamp":ts.isoformat(),"source":"alpaca_stock_iex",
            "age_seconds":round(age,3),"market_derived":True}


async def latest_stock_quote(key,secret,symbol):
    from alpaca_paper_client import _check_credentials
    if not isinstance(symbol,str) or not re.fullmatch(r"[A-Z]{1,5}(?:[.][A-Z])?",symbol):
        raise MarketUnavailable("Unsupported US equity symbol")
    headers=_check_credentials(key,secret)
    try:
        async with httpx.AsyncClient(timeout=8,follow_redirects=False) as client:
            response=await client.get(
                DATA_ORIGIN+"/v2/stocks/"+symbol+"/quotes/latest",
                params={"feed":"iex"},headers=headers)
    except httpx.HTTPError as exc:
        raise MarketUnavailable("Alpaca IEX stock quotes unavailable") from exc
    if response.status_code!=200:
        raise MarketUnavailable("Alpaca IEX quote not available for this account")
    return parse_stock_quote(symbol,response.json())


async def stock_candles(key,secret,symbol,seconds=60):
    """Closed IEX OHLC bars, not trades or a real-time consolidated quote."""
    from datetime import timedelta
    from alpaca_paper_client import _check_credentials
    if seconds not in (60,300,900) or not isinstance(symbol,str) or not re.fullmatch(r"[A-Z]{1,5}(?:[.][A-Z])?",symbol):
        raise MarketUnavailable("Unsupported stock chart timeframe or symbol")
    headers=_check_credentials(key,secret)
    now=datetime.now(timezone.utc)
    try:
        async with httpx.AsyncClient(timeout=10,follow_redirects=False) as client:
            response=await client.get(
                DATA_ORIGIN+"/v2/stocks/"+symbol+"/bars",
                params={
                    "timeframe":{60:"1Min",300:"5Min",900:"15Min"}[seconds],
                    "feed":"iex","limit":120,"sort":"desc",
                    "start":(now-timedelta(days=10)).isoformat(),
                    "end":now.isoformat(),
                },headers=headers)
    except httpx.HTTPError as exc:
        raise MarketUnavailable("Alpaca IEX stock history unavailable") from exc
    if response.status_code!=200:
        raise MarketUnavailable("Alpaca market data access denied or unavailable")
    response_data=response.json()
    if not isinstance(response_data,dict) or not isinstance(response_data.get("bars"),list):
        raise MarketUnavailable("Invalid stock candle payload")
    rows=[]
    for bar in response_data["bars"][:120]:
        if not isinstance(bar,dict):
            continue
        try:
            start=_time(bar["t"])
            if (now-start).total_seconds()<seconds:
                continue
            o,h,l,c=(float(bar[k]) for k in ("o","h","l","c"))
            if not all(__import__("math").isfinite(v) and v>0 for v in (o,h,l,c)):
                continue
            if h<max(o,c) or l>min(o,c):
                continue
            volume=float(bar.get("v",0))
            if not __import__("math").isfinite(volume) or volume<0:
                continue
        except (TypeError,KeyError,ValueError,OverflowError,MarketUnavailable):
            continue
        rows.append({"time":int(start.timestamp()),"open":o,"high":h,"low":l,
                     "close":c,"volume":volume})
    rows.sort(key=lambda x:x["time"])
    return {"symbol":symbol,"granularity":seconds,"source":"alpaca_stock_iex",
            "fetched_at":now.isoformat(),"candles":rows[-120:],
            "last_closed_bar_time":datetime.fromtimestamp(rows[-1]["time"],timezone.utc).isoformat() if rows else None,
            "note":"IEX-only historical bars; gaps and venue coverage possible, not consolidated market data."}
