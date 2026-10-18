"""KAOS Market Intelligence Centre API (research only, never places orders).

Scanners either read request-time authorized candles or previously ingested
collector observations. When a provider is not configured, the endpoint says so
and returns no rows instead of inventing market data.
"""
import asyncio
import os
import re
from datetime import datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

import market_data
from auth import get_current_user
from db import db, new_id, now, now_iso
from kaos_market_intel import (SIGNAL_CODES, alert_matches, options_research,
                               scan_markets, social_activity)
from kaos_rate_limit import SlidingWindowLimiter
from services import get_setting, notify
from services_trading import get_entitlements

router = APIRouter(prefix="/api/v1/intelligence", tags=["market-intelligence"])

CRYPTO_UNIVERSE = ("BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD",
                   "DOGE-USD", "ADA-USD", "AVAX-USD", "LINK-USD")
DEFAULT_STOCKS = ("AAPL", "MSFT", "NVDA", "SPY", "QQQ", "TSLA", "AMD", "META")
MAX_SCAN_SYMBOLS = 8
SYMBOL = re.compile(r"^[A-Z][A-Z0-9.\-]{0,14}$")
UNDERLYING = re.compile(r"^[A-Z]{1,6}$")
WATCHLIST_LIMITS = {
    "free": {"lists": 2, "symbols": 15},
    "pro": {"lists": 10, "symbols": 50},
    "ultimate": {"lists": 25, "symbols": 100},
}
MAX_ALERTS = 20
ALERT_KINDS = ("price_above", "price_below", "breakout_20", "unusual_volume",
               "social_velocity", "signal")

SCAN_LIMITER = SlidingWindowLimiter(limit=12, window_seconds=60)
WRITE_LIMITER = SlidingWindowLimiter(limit=60, window_seconds=60)


async def member(user: dict = Depends(get_current_user)) -> dict:
    if not (await get_entitlements(user)).get("scanners"):
        raise HTTPException(403, "Market Intelligence scanners require a Pro or Ultimate membership")
    return user


def _enforce(limiter: SlidingWindowLimiter, key: str):
    allowed, retry = limiter.check(key)
    if not allowed:
        raise HTTPException(429, f"Too many intelligence requests; retry in {retry}s",
                            headers={"Retry-After": str(retry)})


async def _source_enabled(provider: str) -> bool:
    settings = await get_setting("intel_sources", {}) or {}
    return settings.get(provider, True) is not False


def _annotate(rows, current):
    for row in rows:
        try:
            as_of = datetime.fromisoformat(row["as_of"])
        except (KeyError, TypeError, ValueError):
            continue
        age = max(0.0, (current - as_of).total_seconds() / 60)
        row["age_minutes"] = round(age, 1)
        row["freshness"] = "recent" if age <= 30 else "stale_or_market_closed"
    return rows


def _requested(raw, universe, default):
    if not raw:
        return list(default)
    items = list(dict.fromkeys(x.strip().upper() for x in str(raw).split(",") if x.strip()))
    if not items:
        raise HTTPException(422, "Supply at least one symbol")
    if len(items) > MAX_SCAN_SYMBOLS:
        raise HTTPException(422, f"At most {MAX_SCAN_SYMBOLS} symbols per scan")
    invalid = [x for x in items if x not in universe]
    if invalid:
        raise HTTPException(422, f"Unsupported symbols: {', '.join(invalid)}. Allowed: {', '.join(universe)}")
    return items


def normalize_symbol(value: str) -> str:
    symbol = str(value or "").strip().upper()
    if not SYMBOL.fullmatch(symbol):
        raise HTTPException(422, "Symbol must be 1-15 characters, starting with a letter")
    return symbol


def _limits(entitlements: dict) -> dict:
    tier = entitlements.get("tier") or "free"
    return WATCHLIST_LIMITS.get(tier, WATCHLIST_LIMITS["free"])


# ---------------------------------------------------------------- catalog
@router.get("/center/catalog")
async def catalog(user: dict = Depends(member)):
    alpaca_configured = bool(os.environ.get(market_data.ALPACA_KEY_ENV)
                             and os.environ.get(market_data.ALPACA_SECRET_ENV))
    collector_configured = bool(os.environ.get("KAOS_COLLECTOR_KEY"))
    sources = await get_setting("intel_sources", {}) or {}

    def status(provider, ready, ready_status, missing_status):
        if sources.get(provider) is False:
            return {"data_status": "disabled_by_admin", "requires": []}
        return {"data_status": ready_status if ready else missing_status,
                "requires": [] if ready else ["server operator configuration"]}

    return {
        "research_only": True,
        "execution_enabled": False,
        "modules": [
            {"key": "stocks", "name": "Stock Scanner",
             "coverage": "Up to 8 stock/ETF symbols per scan, 1-minute bars",
             **status("alpaca", alpaca_configured, "provider_configured", "provider_not_configured"),
             "required_env": [market_data.ALPACA_KEY_ENV, market_data.ALPACA_SECRET_ENV]},
            {"key": "crypto", "name": "Crypto Scanner",
             "coverage": "Public Coinbase products, up to 8 symbols per scan",
             "data_status": "live_public_feed" if sources.get("coinbase_public") is not False
                            else "disabled_by_admin", "requires": []},
            {"key": "social", "name": "Social Scanner",
             "coverage": "Stored collector observations only; not platform-wide",
             "data_status": "ingested_observations" if collector_configured
                            else "collector_not_configured",
             "requires": [] if collector_configured else ["KAOS_COLLECTOR_KEY"]},
            {"key": "options", "name": "Options Research",
             "coverage": "Stored Tradier chain snapshots; no Greeks stored",
             "data_status": "ingested_observations" if os.environ.get("TRADIER_TOKEN")
                            else "provider_not_configured",
             "requires": [] if os.environ.get("TRADIER_TOKEN") else ["TRADIER_TOKEN"]},
            {"key": "radar", "name": "Opportunity Radar",
             "coverage": "Fusion of ingested evidence; see /opportunities",
             "data_status": "ingested_observations", "requires": []},
        ],
        "notes": [
            "Scanner scores rank research attention, not the probability of a profitable trade.",
            "No endpoint here can submit, modify or cancel a broker order.",
            "Options Greeks and trade-side data are not stored and are never estimated.",
        ],
    }


# ---------------------------------------------------------------- crypto
async def _crypto_market(symbol, granularity, semaphore):
    async with semaphore:
        try:
            payload = await market_data.get_candles(symbol, "CRYPTO_SPOT", granularity)
        except market_data.QuoteUnavailable as exc:
            return symbol, None, str(exc)
        return symbol, market_data.scanner_candles(payload["candles"]), None


@router.get("/scanners/crypto")
async def crypto_scan(symbols: str | None = None,
                      granularity: int = Query(60),
                      user: dict = Depends(member)):
    _enforce(SCAN_LIMITER, f"crypto:{user['id']}")
    if granularity not in (60, 300, 900):
        raise HTTPException(422, "granularity must be 60, 300 or 900 seconds")
    if not await _source_enabled("coinbase_public"):
        return {"module": "crypto_scanner", "research_only": True, "rows": [], "errors": [],
                "data_status": "disabled_by_admin",
                "note": "A KAOS administrator disabled the public Coinbase source."}
    wanted = _requested(symbols, CRYPTO_UNIVERSE, CRYPTO_UNIVERSE[:6])
    semaphore = asyncio.Semaphore(4)
    current = now()
    fetched = await asyncio.gather(*[_crypto_market(s, granularity, semaphore) for s in wanted])
    result = scan_markets([(s, candles, error) for s, candles, error in fetched],
                          asset_class="crypto", interval_seconds=granularity, now=current)
    _annotate(result["rows"], current)
    return {
        "module": "crypto_scanner",
        "research_only": True,
        "execution_enabled": False,
        "data_status": "live" if result["rows"] else "provider_unavailable",
        "source": "Coinbase Exchange public candles",
        "source_url": "https://docs.cdp.coinbase.com/exchange/reference/exchangerestapi_getproductcandles",
        "fetched_at": current.isoformat(),
        "granularity": granularity,
        "universe": list(CRYPTO_UNIVERSE),
        "coverage_note": ("Sampled public crypto products only; not all crypto markets. "
                          "Public exchange data, not Pocket Option OTC pricing."),
        **result,
    }


# ---------------------------------------------------------------- stocks
@router.get("/scanners/stocks")
async def stock_scan(symbols: str | None = None, user: dict = Depends(member)):
    _enforce(SCAN_LIMITER, f"stocks:{user['id']}")
    if not await _source_enabled("alpaca"):
        return {"module": "stock_scanner", "research_only": True, "rows": [], "errors": [],
                "data_status": "disabled_by_admin",
                "note": "A KAOS administrator disabled the Alpaca market-data source."}
    try:
        wanted = market_data.validate_stock_symbols(
            (symbols or ",".join(DEFAULT_STOCKS)).split(","))
    except market_data.QuoteUnavailable as exc:
        raise HTTPException(422, str(exc)) from exc
    current = now()
    try:
        payload = await market_data.get_stock_candles(wanted, minutes=180)
    except market_data.ProviderNotConfigured as exc:
        return {"module": "stock_scanner", "research_only": True, "rows": [], "errors": [],
                "data_status": "provider_not_configured",
                "required_env": exc.required_env,
                "note": ("The server has no Alpaca market-data credentials, so no stock rows are "
                         "shown. Configure the free Alpaca market-data key to enable this scanner.")}
    except market_data.QuoteUnavailable as exc:
        return {"module": "stock_scanner", "research_only": True, "rows": [], "errors": [],
                "data_status": "provider_unavailable", "note": str(exc)}
    markets = []
    for symbol in wanted:
        candles = payload["candles"].get(symbol) or []
        markets.append((symbol, candles, None if candles else "no completed bars returned (market closed or no data)"))
    result = scan_markets(markets, asset_class="stock", interval_seconds=60, now=current)
    _annotate(result["rows"], current)
    return {
        "module": "stock_scanner",
        "research_only": True,
        "execution_enabled": False,
        "data_status": "live" if result["rows"] else "no_recent_completed_bars",
        "source": payload["source"],
        "feed": payload["feed"],
        "source_url": "https://docs.alpaca.markets/us/reference/stockbars",
        "fetched_at": payload["fetched_at"],
        "coverage_note": payload["coverage_note"],
        **result,
    }


# ---------------------------------------------------------------- social
@router.get("/scanners/social")
async def social_scan(window_minutes: int = Query(60, ge=15, le=1440),
                      limit: int = Query(50, ge=1, le=200),
                      user: dict = Depends(member)):
    _enforce(SCAN_LIMITER, f"social:{user['id']}")
    if not await _source_enabled("bluesky"):
        return {"module": "social_scanner", "research_only": True, "rows": [],
                "data_status": "disabled_by_admin", "aggregation": {}}
    current = now()
    cutoff = (current - timedelta(minutes=window_minutes * 2 + 5)).isoformat()
    records = await db.kaos_intelligence.find(
        {"source": "social", "observed_at": {"$gte": cutoff}},
        {"_id": 0, "asset": 1, "asset_class": 1, "source": 1, "direction": 1, "strength": 1,
         "event_id": 1, "observed_at": 1, "published_at": 1, "source_url": 1},
    ).sort("observed_at", -1).limit(5000).to_list(length=5000)
    aggregation = social_activity(records, now=current, window_minutes=window_minutes)
    return {
        "module": "social_scanner",
        "research_only": True,
        "execution_enabled": False,
        "data_status": "ingested_observations" if aggregation["rows"] else "no_ingested_observations",
        "fetched_at": current.isoformat(),
        "collector_configured": bool(os.environ.get("KAOS_COLLECTOR_KEY")),
        "coverage_note": ("Only social posts already collected by the KAOS collector are counted. "
                          "This is not the whole of Reddit, Bluesky/X or any platform, and a mention "
                          "is not a trading recommendation."),
        "providers_supported": ["bluesky monitored accounts", "Bluesky public search"],
        "rows": aggregation["rows"][:limit],
        "window_minutes": aggregation["window_minutes"],
        "counts_meaning": aggregation["counts_meaning"],
        "skipped_records": aggregation["skipped_records"],
    }


# ---------------------------------------------------------------- options
@router.get("/options/research")
async def options_scan(underlying: str | None = None,
                       limit: int = Query(50, ge=1, le=200),
                       user: dict = Depends(member)):
    _enforce(SCAN_LIMITER, f"options:{user['id']}")
    if underlying is not None:
        underlying = underlying.strip().upper()
        if not UNDERLYING.fullmatch(underlying):
            raise HTTPException(422, "underlying must be a ticker root such as SPY")
    if not await _source_enabled("tradier"):
        return {"module": "options_research", "research_only": True, "rows": [],
                "data_status": "disabled_by_admin"}
    current = now()
    cutoff = (current - timedelta(days=7)).isoformat()
    records = await db.kaos_intelligence.find(
        {"asset_class": "option", "observed_at": {"$gte": cutoff}},
        {"_id": 0, "asset": 1, "asset_class": 1, "source": 1, "direction": 1, "strength": 1,
         "event_id": 1, "observed_at": 1, "published_at": 1, "source_url": 1, "summary": 1},
    ).sort("observed_at", -1).limit(5000).to_list(length=5000)
    result = options_research(records, now=current, underlying=underlying, limit=limit)
    same_day = [row for row in result["rows"] if row["same_day_expiration"]]
    return {
        "module": "options_research",
        "research_only": True,
        "execution_enabled": False,
        "data_status": "ingested_observations" if result["matched"] else "no_ingested_observations",
        "fetched_at": current.isoformat(),
        "underlying": underlying,
        "provider_configured": bool(os.environ.get("TRADIER_TOKEN")),
        "coverage_note": ("Stored Tradier chain snapshots only. Reported volume growth is not "
                          "buyer-initiated flow, and the collector covers a filtered subset of "
                          "nearest-expiration contracts."),
        "spy_0dte_rows": same_day,
        "spy_0dte_available": bool(same_day),
        **result,
    }


# ---------------------------------------------------------------- watchlists
class WatchlistCreate(BaseModel):
    name: str = Field(min_length=1, max_length=40)


class SymbolAdd(BaseModel):
    symbol: str = Field(min_length=1, max_length=15)


@router.get("/watchlists")
async def list_watchlists(user: dict = Depends(get_current_user)):
    limits = _limits(await get_entitlements(user))
    rows = await db.member_watchlists.find({"user_id": user["id"]}, {"_id": 0}).to_list(length=100)
    return {"limits": limits, "watchlists": rows}


@router.post("/watchlists", status_code=201)
async def create_watchlist(body: WatchlistCreate, user: dict = Depends(get_current_user)):
    _enforce(WRITE_LIMITER, f"watchlist-write:{user['id']}")
    limits = _limits(await get_entitlements(user))
    count = await db.member_watchlists.count_documents({"user_id": user["id"]})
    if count >= limits["lists"]:
        raise HTTPException(403, f"Your membership allows {limits['lists']} watchlists")
    name = body.name.strip()
    if not name:
        raise HTTPException(422, "Watchlist name cannot be blank")
    doc = {"id": new_id("wl"), "user_id": user["id"], "name": name, "symbols": [],
           "created_at": now_iso(), "updated_at": now_iso()}
    await db.member_watchlists.insert_one(dict(doc))
    return doc


@router.post("/watchlists/{watchlist_id}/symbols")
async def add_symbol(watchlist_id: str, body: SymbolAdd, user: dict = Depends(get_current_user)):
    _enforce(WRITE_LIMITER, f"watchlist-write:{user['id']}")
    limits = _limits(await get_entitlements(user))
    row = await db.member_watchlists.find_one({"id": watchlist_id, "user_id": user["id"]})
    if not row:
        raise HTTPException(404, "Watchlist not found")
    symbol = normalize_symbol(body.symbol)
    symbols = row.get("symbols") or []
    if symbol not in symbols and len(symbols) >= limits["symbols"]:
        raise HTTPException(403, f"Your membership allows {limits['symbols']} symbols per watchlist")
    await db.member_watchlists.update_one(
        {"id": watchlist_id, "user_id": user["id"]},
        {"$addToSet": {"symbols": symbol}, "$set": {"updated_at": now_iso()}})
    return {"id": watchlist_id, "symbols": list(dict.fromkeys(symbols + [symbol])), "limits": limits}


@router.delete("/watchlists/{watchlist_id}/symbols/{symbol}")
async def remove_symbol(watchlist_id: str, symbol: str, user: dict = Depends(get_current_user)):
    row = await db.member_watchlists.find_one({"id": watchlist_id, "user_id": user["id"]})
    if not row:
        raise HTTPException(404, "Watchlist not found")
    symbol = normalize_symbol(symbol)
    await db.member_watchlists.update_one(
        {"id": watchlist_id, "user_id": user["id"]},
        {"$pull": {"symbols": symbol}, "$set": {"updated_at": now_iso()}})
    return {"id": watchlist_id, "removed": symbol}


@router.delete("/watchlists/{watchlist_id}")
async def delete_watchlist(watchlist_id: str, user: dict = Depends(get_current_user)):
    result = await db.member_watchlists.delete_one({"id": watchlist_id, "user_id": user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(404, "Watchlist not found")
    return {"deleted": watchlist_id}


# ---------------------------------------------------------------- alerts
class AlertCreate(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    kind: Literal["price_above", "price_below", "breakout_20", "unusual_volume",
                  "social_velocity", "signal"]
    symbol: str | None = Field(default=None, max_length=15)
    threshold: float | None = Field(default=None, gt=0, le=1e12)
    signal_code: str | None = Field(default=None, max_length=32)


@router.get("/alerts")
async def list_alerts(user: dict = Depends(member)):
    rows = await db.member_alerts.find({"user_id": user["id"]}, {"_id": 0}).to_list(length=100)
    return {"limits": {"alerts": MAX_ALERTS}, "alerts": rows,
            "note": "Alerts are evaluated when you run a check; KAOS does not run them server-side yet."}


@router.post("/alerts", status_code=201)
async def create_alert(body: AlertCreate, user: dict = Depends(member)):
    _enforce(WRITE_LIMITER, f"alert-write:{user['id']}")
    count = await db.member_alerts.count_documents({"user_id": user["id"]})
    if count >= MAX_ALERTS:
        raise HTTPException(403, f"At most {MAX_ALERTS} alerts are allowed")
    symbol = normalize_symbol(body.symbol) if body.symbol else None
    if body.kind in ("price_above", "price_below"):
        if not symbol or body.threshold is None:
            raise HTTPException(422, "Price alerts need a symbol and a threshold")
    if body.kind == "signal":
        if body.signal_code not in SIGNAL_CODES:
            raise HTTPException(422, f"signal_code must be one of {', '.join(SIGNAL_CODES)}")
    if body.kind == "social_velocity" and symbol and not SYMBOL.fullmatch(symbol):
        raise HTTPException(422, "Invalid symbol")
    doc = {"id": new_id("alrt"), "user_id": user["id"], "name": body.name.strip(),
           "kind": body.kind, "symbol": symbol, "threshold": body.threshold,
           "signal_code": body.signal_code if body.kind == "signal" else None,
           "created_at": now_iso(), "last_checked_at": None, "last_triggered_at": None,
           "delivery": "in_app"}
    await db.member_alerts.insert_one(dict(doc))
    return doc


@router.delete("/alerts/{alert_id}")
async def delete_alert(alert_id: str, user: dict = Depends(member)):
    result = await db.member_alerts.delete_one({"id": alert_id, "user_id": user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(404, "Alert not found")
    return {"deleted": alert_id}


@router.post("/alerts/evaluate")
async def evaluate_alerts(user: dict = Depends(member)):
    _enforce(SCAN_LIMITER, f"alerts:{user['id']}")
    alerts = await db.member_alerts.find({"user_id": user["id"]}, {"_id": 0}).to_list(length=100)
    if not alerts:
        return {"evaluated": 0, "triggered": [], "results": [], "as_of": now_iso(),
                "note": "No alerts are configured yet."}
    current = now()
    symbols = {str(a.get("symbol")) for a in alerts if a.get("symbol")}
    crypto_symbols = [s for s in symbols if s in CRYPTO_UNIVERSE][:MAX_SCAN_SYMBOLS]
    stock_symbols = [s for s in symbols if s not in CRYPTO_UNIVERSE][:MAX_SCAN_SYMBOLS]
    if not crypto_symbols:
        crypto_symbols = list(CRYPTO_UNIVERSE[:4])

    crypto_rows = []
    semaphore = asyncio.Semaphore(4)
    fetched = await asyncio.gather(*[_crypto_market(s, 60, semaphore) for s in crypto_symbols])
    crypto_rows = scan_markets([(s, c, e) for s, c, e in fetched],
                               asset_class="crypto", interval_seconds=60, now=current)["rows"]

    if stock_symbols and await _source_enabled("alpaca"):
        try:
            payload = await market_data.get_stock_candles(stock_symbols, minutes=180)
            crypto_rows += scan_markets(
                [(s, payload["candles"].get(s) or [], None) for s in stock_symbols],
                asset_class="stock", interval_seconds=60, now=current)["rows"]
        except market_data.QuoteUnavailable:
            pass  # stock alerts stay unevaluated rather than being faked

    social_cutoff = (current - timedelta(minutes=125)).isoformat()
    records = await db.kaos_intelligence.find(
        {"source": "social", "observed_at": {"$gte": social_cutoff}},
        {"_id": 0, "asset": 1, "asset_class": 1, "source": 1, "direction": 1, "strength": 1,
         "event_id": 1, "observed_at": 1, "published_at": 1, "source_url": 1},
    ).sort("observed_at", -1).limit(5000).to_list(length=5000)
    social_rows = social_activity(records, now=current)["rows"]

    results, triggered = [], []
    for alert in alerts:
        match = alert_matches(alert, crypto_rows=crypto_rows, social_rows=social_rows, now=current)
        results.append(match)
        await db.member_alerts.update_one(
            {"id": alert["id"], "user_id": user["id"]},
            {"$set": {"last_checked_at": current.isoformat(),
                      "last_result": {k: match.get(k) for k in ("triggered", "reason")}}})
        if not match.get("triggered"):
            continue
        triggered.append(match)
        last = alert.get("last_triggered_at")
        recently_notified = False
        if last:
            try:
                recently_notified = (current - datetime.fromisoformat(last)).total_seconds() < 3600
            except (TypeError, ValueError):
                recently_notified = False
        if not recently_notified:
            await db.member_alerts.update_one(
                {"id": alert["id"], "user_id": user["id"]},
                {"$set": {"last_triggered_at": current.isoformat()}})
            await notify(user["id"], "intel_alert",
                         f"{alert.get('name')}: {match.get('reason')}",
                         link="/dashboard/intelligence")
    return {"evaluated": len(results), "triggered": triggered, "results": results,
            "as_of": current.isoformat(),
            "note": "Checks ran against the latest completed bars and stored social observations only."}
