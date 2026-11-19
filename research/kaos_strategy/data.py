"""Market data layer for the KAOS Strategy study.

Sources (all public, keyless, request-bounded):
  * Crypto  - Coinbase Exchange candles (60s / 300s / 900s / 3600s / 21600s granularity)
  * Equity  - Yahoo Finance chart API (5m / 15m / 60m)
  * FX      - Yahoo Finance chart API (5m / 15m / 60m)

Every series is cached as CSV under data/ so a rerun costs no requests. 4h series are
aggregated from 1h locally, because neither provider serves a native 4h bar.

All series use the same schema: ts (UTC, tz-aware), open, high, low, close, volume.
Bars are returned in ascending time order with no gaps filled and no synthetic rows.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
UA = "KAOS-Research/1.0 (+https://tradingwithkaos.com)"
MIN_INTERVAL = 0.35  # seconds between requests; well inside both providers' limits


def _get(url: str, retries: int = 3) -> bytes:
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as response:
                body = response.read()
            time.sleep(MIN_INTERVAL)
            return body
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
            last = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"request failed: {url} ({last})")


def _path(asset: str, tf: str) -> str:
    return os.path.join(DATA_DIR, f"{asset.replace('/', '_').replace('=', '')}__{tf}.csv")


# --------------------------------------------------------------------------- crypto
COINBASE_GRANULARITY = {"1m": 60, "5m": 300, "15m": 900, "1h": 3600, "6h": 21600}


def fetch_coinbase(product: str, tf: str, bars: int) -> pd.DataFrame:
    """Page backwards from now until `bars` candles or the provider stops returning data."""
    granularity = COINBASE_GRANULARITY[tf]
    base = f"https://api.exchange.coinbase.com/products/{product}/candles"
    rows: list[list[float]] = []
    end = int(time.time()) // granularity * granularity
    while len(rows) < bars:
        span = min(300, bars - len(rows)) * granularity
        start = end - span
        url = f"{base}?granularity={granularity}&start={_iso(start)}&end={_iso(end)}"
        chunk = json.loads(_get(url))
        if not chunk:
            break
        rows.extend(chunk)
        end = start
        if start <= 0:
            break
    # Coinbase returns [time, low, high, open, close, volume] newest-first.
    df = pd.DataFrame(rows, columns=["ts", "low", "high", "open", "close", "volume"])
    df = df.drop_duplicates("ts").sort_values("ts")
    df["ts"] = pd.to_datetime(df["ts"], unit="s", utc=True)
    return df.tail(bars).reset_index(drop=True)


def _iso(epoch: int) -> str:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ------------------------------------------------------------------- equity and FX
YAHOO_INTERVAL = {"1m": "1m", "5m": "5m", "15m": "15m", "1h": "60m"}
YAHOO_RANGE = {"1m": "7d", "5m": "60d", "15m": "60d", "1h": "730d"}


def fetch_yahoo(symbol: str, tf: str) -> pd.DataFrame:
    interval, span = YAHOO_INTERVAL[tf], YAHOO_RANGE[tf]
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/"
           f"{urllib.parse.quote(symbol)}?interval={interval}&range={span}&includePrePost=false")
    payload = json.loads(_get(url))
    result = (payload.get("chart") or {}).get("result") or []
    if not result:
        raise RuntimeError(f"yahoo returned no result for {symbol} {tf}: {payload.get('chart', {}).get('error')}")
    res = result[0]
    quote = (res.get("indicators", {}).get("quote") or [{}])[0]
    df = pd.DataFrame({
        "ts": pd.to_datetime(res["timestamp"], unit="s", utc=True),
        "open": quote.get("open"),
        "high": quote.get("high"),
        "low": quote.get("low"),
        "close": quote.get("close"),
        "volume": quote.get("volume"),
    })
    df = df.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)
    df["volume"] = df["volume"].fillna(0)
    return df


# ------------------------------------------------------------------------ registry
CRYPTO = {"BTCUSD": "BTC-USD", "ETHUSD": "ETH-USD", "SOLUSD": "SOL-USD", "XRPUSD": "XRP-USD"}
EQUITY = {"AAPL": "AAPL", "MSFT": "MSFT", "NVDA": "NVDA", "SPY": "SPY", "QQQ": "QQQ", "TSLA": "TSLA"}
FX = {"EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X", "USDJPY": "USDJPY=X", "AUDUSD": "AUDUSD=X"}

ASSETS = {}
ASSETS.update({k: ("crypto", v) for k, v in CRYPTO.items()})
ASSETS.update({k: ("equity", v) for k, v in EQUITY.items()})
ASSETS.update({k: ("fx", v) for k, v in FX.items()})

# Sample length per timeframe, chosen to fit provider limits without fabricating bars.
CRYPTO_BARS = {"1m": 20000, "5m": 12000, "15m": 8000, "1h": 6000}


def load(asset: str, tf: str, force: bool = False) -> pd.DataFrame:
    """Return a cached OHLCV frame, fetching it once if absent."""
    cache = _path(asset, tf)
    if os.path.exists(cache) and not force:
        df = pd.read_csv(cache, parse_dates=["ts"])
        return df
    os.makedirs(DATA_DIR, exist_ok=True)
    kind, ticker = ASSET_LOOKUP(asset)
    if tf == "4h":
        base = load(asset, "1h", force=force)
        df = resample(base, "4h")
    elif kind == "crypto":
        df = fetch_crypto(ticker, asset, base_timeframe_for_4h(tf, asset))
    else:
        df = fetch_yahoo(ticker, tf)
        if tf == "1d":
            df = fetch_yahoo(ticker, "1h")
            df = resample(df, "1d")
    df.to_csv(cache, index=False)
    return df


def ASSET_LOOKUP(asset: str):
    if asset not in ASSETS:
        raise KeyError(f"unknown asset {asset}")
    return ASSETS[asset]


def fetch_crypto(product: str, asset: str, tf: str) -> pd.DataFrame:
    bars = CRYPTO_BARS.get(tf, 5000)
    return fetch_coinbase(product, tf, bars)


def base_timeframe_for_4h(tf: str, asset: str) -> str:
    return "1h" if tf == "4h" else tf


def resample(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    """Aggregate bars to a coarser fixed UTC window (used for 4h and 1d)."""
    out = (df.set_index("ts").resample(rule, label="left", closed="left")
             .agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
             .dropna()
             .reset_index())
    return out


def available(asset: str, tf: str) -> bool:
    return os.path.exists(_path(asset, tf))


if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)
    for asset in ASSETS:
        for tf in ("1m", "5m", "15m", "1h", "4h"):
            try:
                df = load(asset, tf)
                print(f"{asset:7s} {tf:3s} bars={len(df):6d} {df.ts.iloc[0]} -> {df.ts.iloc[-1]}")
            except Exception as exc:
                print(f"{asset:7s} {tf:3s} FAILED {exc}")
