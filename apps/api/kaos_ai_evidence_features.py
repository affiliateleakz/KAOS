"""Point-in-time, source-aware KAOS AI evidence feature snapshots.

This is a deterministic research preparation layer, NOT a prediction model,
trade signal, inference endpoint or broker order authority. It never fills
missing evidence with a synthetic neutral/zero feature.
"""
from datetime import datetime, timezone
from math import isfinite

from kaos_opportunity import SOURCES, utc
from kaos_source_health import SOURCE_AGE_MINUTES

SCHEMA = "kaos_ai_evidence_snapshot_v1"
ASSET_CLASSES = frozenset(("stock", "etf", "crypto", "forex", "option", "binary_option"))
DIRECTIONS = frozenset(("bullish", "bearish", "neutral"))
MAX_EVENTS = 5000
MAX_EVENTS_PER_CATEGORY = 100
MAX_AGE_DAYS = 3650


def _timestamp(value):
    return utc(value)


def make_feature_snapshot(*, symbol, asset_class, decision_at, observations,
                          candle_source=None, candle_end_at=None):
    """Create a leakage-safe summary of *actually available* evidence.

    All observations must have a source-provided publication timestamp;
    event timestamps alone do not establish availability to a trader.
    Evidence first seen after decision_at is excluded even if the associated
    filing/trade/news event occurred earlier. Untrusted or malformed inputs
    are excluded, and missing categories are explicitly reported.
    """
    decision = _timestamp(decision_at)
    if decision > datetime.now(timezone.utc):
        raise ValueError("Decision timestamp is in the future")
    if not isinstance(symbol, str) or not 1 <= len(symbol) <= 32:
        raise ValueError("Invalid symbol")
    if asset_class not in ASSET_CLASSES:
        raise ValueError("Unsupported asset class")
    if not isinstance(observations, list) or len(observations) > MAX_EVENTS:
        raise ValueError("Evidence collection exceeds limit")

    if candle_end_at is not None:
        candle_end = _timestamp(candle_end_at)
        if candle_end > decision:
            raise ValueError("Future/open candle cannot contribute to snapshot")
    else:
        candle_end = None

    seen = set()
    groups = {source: [] for source in sorted(SOURCES)}
    rejected = {"future_or_unpublished": 0, "invalid": 0, "duplicate": 0,
                "wrong_asset": 0, "too_old": 0, "category_capped": 0}
    for event in observations:
        if not isinstance(event, dict):
            rejected["invalid"] += 1
            continue
        source = event.get("source")
        direction = event.get("direction")
        if source not in SOURCES or direction not in DIRECTIONS:
            rejected["invalid"] += 1
            continue
        if event.get("symbol") != symbol or event.get("asset_class") != asset_class:
            rejected["wrong_asset"] += 1
            continue
        try:
            published = _timestamp(event["published_at"])
            observed = _timestamp(event["observed_at"])
            happened = _timestamp(event["event_at"])
            strength = float(event["strength"])
            event_id = event["event_id"]
            provider = event["provider"]
            if not isinstance(event_id, str) or not event_id or len(event_id) > 200:
                raise ValueError("Missing event id")
            if not isinstance(provider, str) or not provider or len(provider) > 80:
                raise ValueError("Missing source provider")
            if not isfinite(strength) or not 0 <= strength <= 1:
                raise ValueError("Invalid strength")
        except (KeyError, ValueError, TypeError, OverflowError):
            rejected["invalid"] += 1
            continue
        # Strictly point-in-time: event happened, was published and observed
        # before decision; a backdated filing is NOT earlier knowledge.
        if max(published, observed, happened) > decision:
            rejected["future_or_unpublished"] += 1
            continue
        available = max(published, observed)
        age = (decision - available).total_seconds()
        if age > MAX_AGE_DAYS * 86400:
            rejected["too_old"] += 1
            continue
        key = (source, provider, event_id)
        if key in seen:
            rejected["duplicate"] += 1
            continue
        seen.add(key)
        if len(groups[source]) >= MAX_EVENTS_PER_CATEGORY:
            rejected["category_capped"] += 1
            continue
        freshness = SOURCE_AGE_MINUTES.get(source, 60) * 60
        groups[source].append({
            "event_id": event_id, "provider": provider,
            "direction": direction, "strength": strength,
            "available_at": available.isoformat(),
            "event_at": happened.isoformat(),
            "fresh": age <= freshness,
            "age_seconds": round(age, 2),
        })

    categories = {}
    for source, events in groups.items():
        fresh = [e for e in events if e["fresh"]]
        # One event provider cannot masquerade as multiple independent feeds.
        by_provider = {}
        for event in fresh:
            item = by_provider.setdefault(event["provider"], {"bullish": 0.0,
                "bearish": 0.0, "neutral": 0.0})
            item[event["direction"]] = max(item[event["direction"]], event["strength"])
        categories[source] = {
            "state": "missing" if not events else "fresh" if fresh else "stale",
            "events_seen": len(events), "events_fresh": len(fresh),
            "independent_providers": len(by_provider),
            "bullish_evidence": round(sum(p["bullish"] for p in by_provider.values()), 4) if fresh else None,
            "bearish_evidence": round(sum(p["bearish"] for p in by_provider.values()), 4) if fresh else None,
            "last_available_at": max((e["available_at"] for e in events), default=None),
        }
    return {
        "schema": SCHEMA, "symbol": symbol, "asset_class": asset_class,
        "decision_at": decision.isoformat(), "candle_source": candle_source,
        "candle_end_at": candle_end.isoformat() if candle_end else None,
        "categories": categories, "rejected": rejected,
        "source_coverage": {
            "fresh": sorted(s for s, v in categories.items() if v["state"] == "fresh"),
            "stale": sorted(s for s, v in categories.items() if v["state"] == "stale"),
            "missing": sorted(s for s, v in categories.items() if v["state"] == "missing"),
        },
        "research_only": True, "execution_enabled": False,
        "signal_authorized": False, "prediction_available": False,
        "note": "Evidence inputs are not calibrated price probabilities or trading signals.",
    }
