"""Authorized market-data quotes for market-data-driven paper fills.

First (and currently only) source: Coinbase Exchange's public ticker endpoint
(no account or API key, crypto spot only). Other asset classes have no
authorized feed yet and are refused rather than simulated.
"""
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

import httpx

COINBASE_PUBLIC_SOURCE = "coinbase_exchange_public_ticker"
COINBASE_TICKER_URL = "https://api.exchange.coinbase.com/products/{product}/ticker"
CRYPTO_PRODUCT = re.compile(r"^[A-Z0-9]{2,10}-[A-Z]{3,5}$")


class QuoteUnavailable(Exception):
    pass


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


fetch_crypto_quote = _fetch_coinbase  # swapped in tests


async def get_quote(symbol: str, asset_class: str) -> Quote:
    symbol = symbol.upper()
    if asset_class != "CRYPTO_SPOT":
        raise QuoteUnavailable(f"No authorized market-data feed for {asset_class} yet; use the manual paper demo")
    if not CRYPTO_PRODUCT.match(symbol):
        raise QuoteUnavailable("Crypto symbols use the Coinbase product format, e.g. BTC-USD")
    return await fetch_crypto_quote(symbol)
