"""KAOS Market Intelligence Centre: deterministic scanners over verified inputs.

Two input paths exist, and this module never mixes them up:

1. Request-time closed candles (crypto from the public Coinbase Exchange API,
   stocks/ETFs from Alpaca only when the server has market-data keys). Every row
   carries its own source, as-of time and bar count.
2. Observations already ingested by the out-of-process collectors into
   ``kaos_intelligence``. Social, options and news rows are read from there only;
   this module never invents mentions, chain data, Greeks or sentiment.

Everything here is research output. Scores rank research attention, not the
probability of a winning trade, and no function can submit a broker order.
"""
import re
from datetime import date, datetime, timedelta, timezone
from math import isfinite, sqrt
from statistics import median as _median

from kaos_opportunity import utc

MIN_BARS = 25
MIN_BARS_TREND = 50
SOCIAL_WINDOW_MINUTES = 60
OCC_SYMBOL = re.compile(r"^([A-Z]{1,6})(\d{6})([CP])(\d{8})$")
SIGNAL_CODES = (
    "BREAKOUT_20", "BREAKDOWN_20", "FAILED_BREAKOUT", "UNUSUAL_VOLUME",
    "VOLUME_ANOMALY", "MOMENTUM_UP", "MOMENTUM_DOWN", "VOLATILITY_EXPANSION",
    "NEAR_RESISTANCE", "NEAR_SUPPORT", "TREND_UP", "TREND_DOWN",
)


class InsufficientData(Exception):
    """Raised when a symbol cannot be scored from verified completed candles."""


def validate_candles(candles):
    """Accept strictly increasing, finite, positive OHLC bars; reject anything else."""
    if not isinstance(candles, list):
        raise ValueError("Candle list required")
    cleaned = []
    previous = None
    for candle in candles:
        try:
            ts = int(candle["ts"])
            o, h, l, c = (float(candle[k]) for k in ("open", "high", "low", "close"))
            volume = float(candle.get("volume", 0) or 0)
        except (KeyError, TypeError, ValueError, OverflowError):
            raise ValueError("Invalid OHLC candle") from None
        if not all(isfinite(v) for v in (o, h, l, c, volume)):
            raise ValueError("Invalid OHLC price")
        if min(o, h, l, c) <= 0 or volume < 0 or l > min(o, c) or h < max(o, c):
            raise ValueError("Invalid OHLC price")
        if previous is not None and ts <= previous:
            raise ValueError("Candles must be strictly increasing without duplicate timestamps")
        previous = ts
        cleaned.append({"ts": ts, "open": o, "high": h, "low": l, "close": c, "volume": volume})
    return cleaned


def ema(values, period):
    if len(values) < period:
        return None
    value = sum(values[:period]) / period
    alpha = 2 / (period + 1)
    for price in values[period:]:
        value = alpha * price + (1 - alpha) * value
    return value


def atr(candles, period=14):
    """Wilder ATR over completed bars; None when history is too short."""
    if len(candles) < period + 1:
        return None
    true_ranges = []
    for index in range(1, len(candles)):
        high, low, prev_close = candles[index]["high"], candles[index]["low"], candles[index - 1]["close"]
        true_ranges.append(max(high - low, abs(high - prev_close), abs(low - prev_close)))
    value = sum(true_ranges[:period]) / period
    alpha = 1 / period
    for tr in true_ranges[period:]:
        value = alpha * tr + (1 - alpha) * value
    return value


def _pct_change(closes, bars):
    if len(closes) <= bars or closes[-bars] <= 0:
        return None
    return (closes[-1] / closes[-bars] - 1) * 100


def _stdev(values):
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return sqrt(sum((v - mean) ** 2 for v in values) / len(values))


def parse_occ_symbol(symbol):
    """Parse a standard OCC option symbol; returns None when the format is unknown."""
    match = OCC_SYMBOL.match(str(symbol or "").upper())
    if not match:
        return None
    try:
        expiry = datetime.strptime(match.group(2), "%y%m%d").date()
    except ValueError:
        return None
    return {"root": match.group(1), "expiration": expiry,
            "option_type": "call" if match.group(3) == "C" else "put"}


def technical_row(symbol, candles, *, asset_class, interval_seconds, now=None):
    """Score one symbol from completed candles.

    ``candles[-1]`` is the most recent *closed* bar; its ``ts`` is the bar's open
    time, so the row's as-of timestamp is ``ts + interval``.
    """
    now = utc(now or datetime.now(timezone.utc))
    bars = validate_candles(candles)
    if len(bars) < MIN_BARS:
        raise InsufficientData(f"At least {MIN_BARS} completed bars are required")
    if interval_seconds not in (60, 300, 900):
        raise ValueError("Unsupported interval")

    closes = [b["close"] for b in bars]
    last = bars[-1]
    as_of = datetime.fromtimestamp(last["ts"] / 1000, tz=timezone.utc) + timedelta(seconds=interval_seconds)
    if as_of > now + timedelta(seconds=5):
        raise ValueError("Candle close time is in the future")

    prior = bars[-21:-1]
    prior_high = max(b["high"] for b in prior)
    prior_low = min(b["low"] for b in prior)
    prior_volumes = [b["volume"] for b in prior]
    median_volume = _median(prior_volumes)
    volume_ratio = last["volume"] / median_volume if median_volume > 0 else None
    volume_zscore = None
    if len(prior_volumes) >= 2:
        spread = _stdev(prior_volumes)
        if spread > 0:
            volume_zscore = (last["volume"] - sum(prior_volumes) / len(prior_volumes)) / spread

    atr_value = atr(bars)
    atr_pct = atr_value / last["close"] * 100 if atr_value else None
    prior_ranges = [b["high"] - b["low"] for b in prior]
    median_range = _median(prior_ranges)
    last_range = last["high"] - last["low"]
    range_ratio = last_range / median_range if median_range > 0 else None
    body = last["close"] - last["open"]
    close_location = ((last["close"] - last["low"]) / last_range) if last_range > 0 else None

    ema20 = ema(closes, 20)
    ema50 = ema(closes, MIN_BARS_TREND)
    ema20_ago = ema(closes[:-5], 20)
    trend = "insufficient_history"
    if ema50 is not None and ema20_ago is not None:
        if ema20 > ema50 and ema20 > ema20_ago:
            trend = "up"
        elif ema20 < ema50 and ema20 < ema20_ago:
            trend = "down"
        else:
            trend = "flat"

    change5 = _pct_change(closes, 5)
    change15 = _pct_change(closes, 15)
    structure = "inside_range"
    if last["close"] > prior_high:
        structure = "breakout"
    elif last["close"] < prior_low:
        structure = "breakdown"
    elif last["high"] > prior_high and last["close"] < prior_high:
        structure = "failed_breakout"
    elif last["low"] < prior_low and last["close"] > prior_low:
        structure = "failed_breakdown"

    proximity = 0.0025
    position = "mid_range"
    if abs(last["close"] - prior_high) / last["close"] <= proximity:
        position = "near_resistance"
    elif abs(last["close"] - prior_low) / last["close"] <= proximity:
        position = "near_support"

    price_action = "normal"
    if range_ratio is not None and range_ratio >= 1.5:
        price_action = "expansion"
    elif range_ratio is not None and range_ratio <= 0.6:
        price_action = "compression"

    signals = []

    def add(code, direction, evidence):
        signals.append({"code": code, "direction": direction,
                        "label": code.replace("_", " ").title(), "evidence": evidence})

    if structure == "breakout":
        add("BREAKOUT_20", "bullish", f"Closed above the prior 20-bar high {prior_high:.6g}")
    if structure == "breakdown":
        add("BREAKDOWN_20", "bearish", f"Closed below the prior 20-bar low {prior_low:.6g}")
    if structure == "failed_breakout":
        add("FAILED_BREAKOUT", "bearish", f"Traded above {prior_high:.6g} but closed back below it")
    if volume_ratio is not None and volume_ratio >= 2:
        add("UNUSUAL_VOLUME", "neutral", f"Volume {volume_ratio:.2f}x the prior 20-bar median")
    if volume_zscore is not None and volume_zscore >= 3:
        add("VOLUME_ANOMALY", "neutral", f"Volume {volume_zscore:.2f} standard deviations above the prior 20 bars")
    if change5 is not None and change5 >= 0.35:
        add("MOMENTUM_UP", "bullish", f"5-bar change {change5:.2f}%")
    if change5 is not None and change5 <= -0.35:
        add("MOMENTUM_DOWN", "bearish", f"5-bar change {change5:.2f}%")
    if price_action == "expansion":
        add("VOLATILITY_EXPANSION", "neutral", f"Bar range {range_ratio:.2f}x the prior 20-bar median")
    if position == "near_resistance":
        add("NEAR_RESISTANCE", "neutral", f"Within {proximity:.2%} of resistance {prior_high:.6g}")
    if position == "near_support":
        add("NEAR_SUPPORT", "neutral", f"Within {proximity:.2%} of support {prior_low:.6g}")
    if trend == "up":
        add("TREND_UP", "bullish", f"EMA20 {ema20:.6g} above EMA50 {ema50:.6g} and rising")
    if trend == "down":
        add("TREND_DOWN", "bearish", f"EMA20 {ema20:.6g} below EMA50 {ema50:.6g} and falling")

    # Attention rank only: capped additive weights, never a probability.
    score = 0.0
    if volume_ratio is not None:
        score += min(25.0, max(0.0, volume_ratio - 1) * 25)
    if structure in ("breakout", "breakdown"):
        score += 25
    if structure in ("failed_breakout", "failed_breakdown"):
        score += 15
    if change5 is not None:
        score += min(20.0, abs(change5) * 5)
    if atr_pct is not None:
        score += min(15.0, atr_pct * 2)
    if range_ratio is not None:
        score += min(15.0, max(0.0, range_ratio - 1) * 10)

    return {
        "symbol": str(symbol).upper(),
        "asset_class": asset_class,
        "data_status": "ok",
        "as_of": as_of.isoformat(),
        "bar_open": datetime.fromtimestamp(last["ts"] / 1000, tz=timezone.utc).isoformat(),
        "interval_seconds": interval_seconds,
        "bars": len(bars),
        "last_close": round(last["close"], 10),
        "change_5_bars_pct": None if change5 is None else round(change5, 4),
        "change_15_bars_pct": None if change15 is None else round(change15, 4),
        "volume_ratio_20": None if volume_ratio is None else round(volume_ratio, 4),
        "volume_zscore_20": None if volume_zscore is None else round(volume_zscore, 4),
        "atr_pct": None if atr_pct is None else round(atr_pct, 4),
        "range_ratio_20": None if range_ratio is None else round(range_ratio, 4),
        "close_location": None if close_location is None else round(close_location, 4),
        "body_direction": "bullish" if body > 0 else "bearish" if body < 0 else "flat",
        "trend": trend,
        "price_action": price_action,
        "structure": structure,
        "position": position,
        "support": round(prior_low, 10),
        "resistance": round(prior_high, 10),
        "sparkline": [round(value, 10) for value in closes[-30:]],
        "signals": signals,
        "attention_score": round(min(100.0, score), 1),
        "score_type": "heuristic_attention_rank_not_probability",
        "research_only": True,
    }


def scan_markets(markets, *, asset_class, interval_seconds, now=None):
    """Score a bounded universe. ``markets`` is [(symbol, candles or None, error)].

    A symbol with no usable candles returns an explicit error row; nothing is
    back-filled with placeholder values.
    """
    now = utc(now or datetime.now(timezone.utc))
    rows, errors = [], []
    for entry in markets:
        symbol, candles = entry[0], entry[1]
        error = entry[2] if len(entry) > 2 else None
        if error:
            errors.append({"symbol": str(symbol).upper(), "reason": str(error)[:200]})
            continue
        try:
            rows.append(technical_row(symbol, candles, asset_class=asset_class,
                                      interval_seconds=interval_seconds, now=now))
        except (InsufficientData, ValueError) as exc:
            errors.append({"symbol": str(symbol).upper(), "reason": str(exc)[:200]})
    rows.sort(key=lambda row: row["attention_score"], reverse=True)
    return {"rows": rows, "errors": errors}


def _provider_of(event_id):
    return str(event_id or "").split(":", 1)[0].lower() or "other"


def social_activity(observations, *, now=None, window_minutes=SOCIAL_WINDOW_MINUTES):
    """Aggregate *ingested* social observations into per-ticker attention rows.

    Counts are distinct stored observation ids, not platform-wide mentions.
    """
    now = utc(now or datetime.now(timezone.utc))
    if not 15 <= window_minutes <= 1440:
        raise ValueError("window_minutes must be between 15 and 1440")
    current_start = now - timedelta(minutes=window_minutes)
    prior_start = current_start - timedelta(minutes=window_minutes)

    grouped = {}
    skipped = 0
    for obs in observations:
        if obs.get("source") != "social":
            continue
        try:
            observed = utc(obs["observed_at"])
            asset = str(obs["asset"]).upper()
            event_id = str(obs["event_id"])
        except (KeyError, TypeError, ValueError):
            skipped += 1
            continue
        if observed > now or observed < prior_start:
            continue
        row = grouped.setdefault(asset, {
            "asset": asset,
            "asset_class": obs.get("asset_class", "stock"),
            "current": {}, "prior": {}, "sources": set(), "providers": set(),
            "direction": {"bullish": 0, "bearish": 0, "neutral": 0},
            "latest_published": None, "latest_url": None, "strength": 0.0,
        })
        bucket = row["current"] if observed >= current_start else row["prior"]
        bucket[event_id] = True
        if observed >= current_start:
            row["sources"].add(str(obs.get("source")))
            row["providers"].add(_provider_of(event_id))
            direction = obs.get("direction")
            if direction in row["direction"]:
                row["direction"][direction] += 1
            try:
                strength = float(obs.get("strength") or 0)
            except (TypeError, ValueError):
                strength = 0.0
            row["strength"] = max(row["strength"], strength)
            published = obs.get("published_at") or obs.get("observed_at")
            if row["latest_published"] is None or str(published) > str(row["latest_published"]):
                row["latest_published"] = published
                row["latest_url"] = obs.get("source_url")

    rows = []
    for asset, row in grouped.items():
        current, prior = len(row["current"]), len(row["prior"])
        if current == 0:
            continue
        if prior == 0:
            change, velocity = None, "new"
        else:
            change = round((current - prior) / prior * 100, 2)
            if current >= prior * 1.5 and current - prior >= 2:
                velocity = "rising"
            elif current <= prior * 0.5 and prior - current >= 2:
                velocity = "falling"
            else:
                velocity = "flat"
        rows.append({
            "asset": asset,
            "asset_class": row["asset_class"],
            "mentions_current_window": current,
            "mentions_prior_window": prior,
            "mention_change_pct": change,
            "velocity": velocity,
            "providers": sorted(row["providers"]),
            "source_categories": sorted(row["sources"]),
            "direction_counts": row["direction"],
            "max_strength": round(min(1.0, max(0.0, row["strength"])), 4),
            "latest_published_at": row["latest_published"],
            "latest_source_url": row["latest_url"],
            "coverage": "ingested_observations_only_not_platform_wide",
        })
    rows.sort(key=lambda row: (row["velocity"] == "rising", row["mentions_current_window"]), reverse=True)
    return {"rows": rows, "window_minutes": window_minutes, "skipped_records": skipped,
            "counts_meaning": "Distinct stored observations per ticker, not total platform mentions"}


def options_research(observations, *, now=None, underlying=None, limit=50):
    """List stored options-activity observations with chain metadata we can verify.

    Greeks, implied volatility and same-day odds are *not* stored by the current
    collector, so they are reported as unavailable instead of estimated.
    """
    now = utc(now or datetime.now(timezone.utc))
    cutoff = now - timedelta(days=7)
    target = str(underlying).upper() if underlying else None
    rows = []
    for obs in observations:
        if obs.get("asset_class") != "option":
            continue
        try:
            observed = utc(obs["observed_at"])
            contract = str(obs["asset"]).upper()
        except (KeyError, TypeError, ValueError):
            continue
        if observed < cutoff or observed > now:
            continue
        parsed = parse_occ_symbol(contract)
        if target and (not parsed or parsed["root"] != target):
            continue
        rows.append({
            "contract": contract,
            "root": parsed["root"] if parsed else None,
            "expiration": parsed["expiration"].isoformat() if parsed else None,
            "option_type": parsed["option_type"] if parsed else None,
            "same_day_expiration": bool(parsed and parsed["expiration"] == now.date()),
            "observed_at": observed.isoformat(),
            "published_at": obs.get("published_at"),
            "direction": obs.get("direction", "neutral"),
            "strength": obs.get("strength"),
            "source_url": obs.get("source_url"),
            "summary": str(obs.get("summary", ""))[:1200],
            "provider": _provider_of(obs.get("event_id")),
            "research_only": True,
        })
    rows.sort(key=lambda row: row["observed_at"], reverse=True)
    return {
        "rows": rows[:max(1, min(200, limit))],
        "matched": len(rows),
        "truncated": len(rows) > limit,
        "metrics_available": ["reported_volume_change", "open_interest", "bid_ask_spread"],
        "metrics_unavailable": ["implied_volatility", "delta", "gamma", "theta", "vega", "trade_side"],
        "unavailable_reason": "The authorized collector stores chain snapshots, not Greeks or trade-side data.",
        "coverage": "ingested_snapshots_only_not_market_wide_flow",
        "research_only": True,
    }


def alert_matches(alert, *, crypto_rows=(), social_rows=(), now=None):
    """Evaluate one stored alert definition against current verified scanner rows."""
    now = utc(now or datetime.now(timezone.utc))
    kind = alert.get("kind")
    symbol = str(alert.get("symbol")).upper() if alert.get("symbol") else None
    threshold = alert.get("threshold")
    reasons = []

    def picked(row):
        return symbol is None or row.get("symbol") == symbol or row.get("asset") == symbol

    if kind in ("price_above", "price_below"):
        if not isinstance(threshold, (int, float)) or isinstance(threshold, bool):
            return {"alert_id": alert.get("id"), "triggered": False, "reason": "Alert has no numeric threshold"}
        for row in crypto_rows:
            if not picked(row):
                continue
            price = row.get("last_close")
            if price is None:
                continue
            hit = price >= threshold if kind == "price_above" else price <= threshold
            if hit:
                reasons.append(f"{row['symbol']} last closed bar {price:g} "
                               f"{'at or above' if kind == 'price_above' else 'at or below'} {threshold:g}")
                return {"alert_id": alert.get("id"), "name": alert.get("name"), "kind": kind,
                        "triggered": True, "symbol": row["symbol"], "as_of": row.get("as_of"),
                        "reason": reasons[0], "research_only": True}
        return {"alert_id": alert.get("id"), "name": alert.get("name"), "kind": kind,
                "triggered": False, "reason": "Condition not met on the latest closed bars"}

    if kind in ("breakout_20", "unusual_volume", "signal"):
        wanted = alert.get("signal_code") if kind == "signal" else {
            "breakout_20": "BREAKOUT_20", "unusual_volume": "UNUSUAL_VOLUME"}[kind]
        if wanted not in SIGNAL_CODES:
            return {"alert_id": alert.get("id"), "triggered": False, "reason": "Unknown signal code"}
        for row in crypto_rows:
            if not picked(row):
                continue
            match = next((s for s in row.get("signals", []) if s.get("code") == wanted), None)
            if match:
                return {"alert_id": alert.get("id"), "name": alert.get("name"), "kind": kind,
                        "triggered": True, "symbol": row["symbol"], "as_of": row.get("as_of"),
                        "reason": f"{wanted}: {match.get('evidence')}", "research_only": True}
        return {"alert_id": alert.get("id"), "name": alert.get("name"), "kind": kind,
                "triggered": False, "reason": f"{wanted} not present on the latest closed bars"}

    if kind == "social_velocity":
        for row in social_rows:
            if not picked(row):
                continue
            if row.get("velocity") == "rising":
                return {"alert_id": alert.get("id"), "name": alert.get("name"), "kind": kind,
                        "triggered": True, "symbol": row["asset"], "as_of": row.get("latest_published_at"),
                        "reason": (f"{row['mentions_current_window']} stored mentions vs "
                                   f"{row['mentions_prior_window']} in the prior window"),
                        "research_only": True}
        return {"alert_id": alert.get("id"), "name": alert.get("name"), "kind": kind,
                "triggered": False, "reason": "No stored social acceleration matched"}

    return {"alert_id": alert.get("id"), "triggered": False, "reason": "Unsupported alert kind"}


def parse_expiration(value):
    """Accept an ISO date string; return None rather than guessing."""
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None
