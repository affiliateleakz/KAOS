"""Authorized market data for paper fills and the Market Intelligence Centre.

Sources: Coinbase Exchange's public ticker/candles endpoints (no account key,
crypto spot only) and Alpaca Market Data for stock/ETF 1-minute bars (server-side
keys required, IEX by default). Anything without a configured authorized source
is refused rather than simulated.
"""
import os
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

import httpx

COINBASE_PUBLIC_SOURCE = "coinbase_exchange_public_ticker"
COINBASE_TICKER_URL = "https://api.exchange.coinbase.com/products/{product}/ticker"
CRYPTO_PRODUCT = re.compile(r"^[A-Z0-9]{2,10}-[A-Z]{3,5}$")

ALPACA_BARS_URL = "https://data.alpaca.markets/v2/stocks/bars"
ALPACA_STOCK_SOURCE = "alpaca_market_data"
ALPACA_KEY_ENV = "APCA_API_KEY_ID"
ALPACA_SECRET_ENV = "APCA_API_SECRET_KEY"
ALPACA_FEED_ENV = "KAOS_ALPACA_FEED"
ALPACA_FEEDS = {"iex", "sip"}
STOCK_SYMBOL = re.compile(r"^[A-Z][A-Z0-9.]{0,11}$")


class QuoteUnavailable(Exception):
    pass


class ProviderNotConfigured(QuoteUnavailable):
    """A server-side market-data provider has no credentials; never faked."""

    def __init__(self, provider: str, required_env: list):
        self.provider = provider
        self.required_env = list(required_env)
        super().__init__(f"{provider} market data is not configured on this server")



@dataclass(frozen=True)
class Quote:
    symbol: str
    bid: Decimal
    ask: Decimal
    last: Decimal
    quote_time: datetime
    fetched_at: datetime
    source: str

    def provenance(self) -> dict:
        d = asdict(self)
        return {k: (v.isoformat() if isinstance(v, datetime) else str(v) if isinstance(v, Decimal) else v)
                for k, v in d.items()}


def _parse_time(value: str) -> datetime:
    # Coinbase returns nanosecond precision ("...45.573353253Z"); trim to microseconds.
    m = re.match(r"^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(\.\d+)?Z$", value or "")
    if not m:
        raise QuoteUnavailable("Market data returned an invalid timestamp")
    frac = (m.group(2) or ".0")[:7]
    return datetime.fromisoformat(m.group(1) + frac).replace(tzinfo=timezone.utc)


def parse_coinbase_ticker(symbol: str, data: dict, fetched_at: datetime) -> Quote:
    try:
        bid, ask, last = (Decimal(str(data[k])) for k in ("bid", "ask", "price"))
    except (KeyError, InvalidOperation, TypeError):
        raise QuoteUnavailable("Market data returned an incomplete quote")
    if not all(x.is_finite() and x > 0 for x in (bid, ask, last)) or ask < bid:
        raise QuoteUnavailable("Market data returned an invalid quote")
    return Quote(symbol, bid, ask, last, _parse_time(data.get("time")), fetched_at, COINBASE_PUBLIC_SOURCE)


async def _fetch_coinbase(symbol: str) -> Quote:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(COINBASE_TICKER_URL.format(product=symbol),
                                 headers={"User-Agent": "kaos-paper-quotes/1.0"})
    except httpx.HTTPError:
        raise QuoteUnavailable("Market data provider unreachable")
    if r.status_code == 404:
        raise QuoteUnavailable(f"Unknown Coinbase product {symbol}")
    if r.status_code != 200:
        raise QuoteUnavailable(f"Market data provider error ({r.status_code})")
    return parse_coinbase_ticker(symbol, r.json(), datetime.now(timezone.utc))


COINBASE_CANDLES_URL = "https://api.exchange.coinbase.com/products/{product}/candles"
GRANULARITIES = {60, 300, 900}


async def _fetch_coinbase_candles(symbol: str, granularity: int) -> list:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(COINBASE_CANDLES_URL.format(product=symbol), params={"granularity": granularity},
                                 headers={"User-Agent": "kaos-paper-quotes/1.0"})
    except httpx.HTTPError:
        raise QuoteUnavailable("Market data provider unreachable")
    if r.status_code != 200:
        raise QuoteUnavailable(f"Market data provider error ({r.status_code})")
    return r.json()


def closed_candles(rows: list, granularity: int, now: datetime) -> list:
    """Coinbase rows are [time, low, high, open, close, volume], newest first. Drop the still-forming bar."""
    out = []
    for t, low, high, op, close, vol in rows:
        if t + granularity <= now.timestamp():
            out.append({"time": int(t), "open": float(op), "high": float(high), "low": float(low),
                        "close": float(close), "volume": float(vol)})
    return sorted(out, key=lambda c: c["time"])


fetch_crypto_quote = _fetch_coinbase  # swapped in tests
fetch_crypto_candles = _fetch_coinbase_candles  # swapped in tests


async def get_candles(symbol: str, asset_class: str, granularity: int = 60) -> dict:
    symbol = symbol.upper()
    if asset_class != "CRYPTO_SPOT":
        raise QuoteUnavailable(f"No authorized market-data feed for {asset_class} yet")
    if not CRYPTO_PRODUCT.match(symbol) or granularity not in GRANULARITIES:
        raise QuoteUnavailable("Unsupported symbol or candle size")
    now = datetime.now(timezone.utc)
    return {"symbol": symbol, "granularity": granularity, "source": COINBASE_PUBLIC_SOURCE, "fetched_at": now.isoformat(),
            "candles": closed_candles(await fetch_crypto_candles(symbol, granularity), granularity, now)}


def scanner_candles(candles: list) -> list:
    """Convert closed Coinbase candle dicts (seconds) to scanner rows (millisecond ts)."""
    return [{"ts": int(c["time"]) * 1000, "open": c["open"], "high": c["high"],
             "low": c["low"], "close": c["close"], "volume": c.get("volume", 0)} for c in candles]


def validate_stock_symbols(symbols) -> list:
    unique = list(dict.fromkeys(str(s).upper().strip() for s in symbols))
    if not unique or len(unique) > 12 or any(not STOCK_SYMBOL.fullmatch(s) for s in unique):
        raise QuoteUnavailable("Supply 1-12 valid stock/ETF symbols")
    return unique


async def _fetch_alpaca_bars(symbols: list, minutes: int, feed: str) -> dict:
    headers = {"APCA-API-KEY-ID": os.environ[ALPACA_KEY_ENV],
               "APCA-API-SECRET-KEY": os.environ[ALPACA_SECRET_ENV],
               "User-Agent": "kaos-market-intel/1.0"}
    now = datetime.now(timezone.utc)
    params = {"symbols": ",".join(symbols), "timeframe": "1Min",
              "start": (now - timedelta(minutes=minutes)).isoformat().replace("+00:00", "Z"),
              "end": now.isoformat().replace("+00:00", "Z"),
              "limit": 1000, "sort": "asc", "feed": feed}
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(ALPACA_BARS_URL, params=params, headers=headers)
    except httpx.HTTPError:
        raise QuoteUnavailable("Alpaca market data is unreachable")
    if response.status_code == 401:
        raise QuoteUnavailable("Alpaca rejected the server market-data credentials")
    if response.status_code == 429:
        raise QuoteUnavailable("Alpaca market-data rate limit reached")
    if response.status_code != 200:
        raise QuoteUnavailable(f"Alpaca market-data error ({response.status_code})")
    try:
        payload = response.json()
    except ValueError:
        raise QuoteUnavailable("Alpaca market data returned invalid JSON")
    if not isinstance(payload, dict) or not isinstance(payload.get("bars"), dict):
        raise QuoteUnavailable("Alpaca market data returned an unexpected shape")
    return payload["bars"]


def _closed_stock_candles(points: list, now: datetime) -> list:
    out = []
    cutoff = now.timestamp()
    for point in points or []:
        try:
            start = datetime.fromisoformat(str(point["t"]).replace("Z", "+00:00"))
            open_, high, low = float(point["o"]), float(point["h"]), float(point["l"])
            close, volume = float(point["c"]), float(point.get("v") or 0)
        except (KeyError, TypeError, ValueError):
            continue
        if start.tzinfo is None or start.timestamp() + 60 > cutoff:
            continue  # still forming: never score an incomplete bar
        out.append({"ts": int(start.timestamp() * 1000), "open": open_, "high": high,
                    "low": low, "close": close, "volume": volume})
    out.sort(key=lambda c: c["ts"])
    return out


async def get_stock_candles(symbols, minutes: int = 180) -> dict:
    """Completed 1-minute stock/ETF bars from Alpaca, only when configured server-side."""
    symbols = validate_stock_symbols(symbols)
    if not 30 <= minutes <= 1440:
        raise QuoteUnavailable("minutes must be between 30 and 1440")
    key, secret = os.environ.get(ALPACA_KEY_ENV), os.environ.get(ALPACA_SECRET_ENV)
    if not key or not secret:
        raise ProviderNotConfigured("Alpaca", [ALPACA_KEY_ENV, ALPACA_SECRET_ENV])
    feed = (os.environ.get(ALPACA_FEED_ENV) or "iex").strip().lower()
    if feed not in ALPACA_FEEDS:
        raise QuoteUnavailable("KAOS_ALPACA_FEED must be iex or sip")
    now = datetime.now(timezone.utc)
    bars = await fetch_stock_bars(symbols, minutes, feed)
    return {"source": ALPACA_STOCK_SOURCE, "feed": feed, "fetched_at": now.isoformat(),
            "coverage_note": ("IEX is a single exchange, not consolidated national volume"
                              if feed == "iex" else "SIP access depends on the Alpaca plan"),
            "candles": {s: _closed_stock_candles(bars.get(s, []), now) for s in symbols}}


fetch_stock_bars = _fetch_alpaca_bars  # swapped in tests


async def get_quote(symbol: str, asset_class: str) -> Quote:
    symbol = symbol.upper()
    if asset_class != "CRYPTO_SPOT":
        raise QuoteUnavailable(f"No authorized market-data feed for {asset_class} yet; use the manual paper demo")
    if not CRYPTO_PRODUCT.match(symbol):
        raise QuoteUnavailable("Crypto symbols use the Coinbase product format, e.g. BTC-USD")
    return await fetch_crypto_quote(symbol)
