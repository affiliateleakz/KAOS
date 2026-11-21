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
