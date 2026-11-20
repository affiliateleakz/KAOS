"""Build time-safe KAOS research datasets from candle and intelligence exports.

No inference deployment, live order routing or automated training. Standard-library
only. Training rows include *observed* news/social history as of each completed bar.
"""
import argparse
import bisect
import json
from datetime import datetime, timezone
from pathlib import Path

HORIZONS = (5, 30, 300, 3600, 14400, 86400)
SOURCES = frozenset(("news", "social"))
WINDOW_MS = 3_600_000


def timestamp_ms(raw):
    """Convert an explicitly timezone-aware ISO timestamp into milliseconds."""
    if isinstance(raw, bool):
        raise ValueError("invalid timestamp")
    if isinstance(raw, str):
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            raise ValueError("timestamp has no timezone")
        return int(dt.timestamp() * 1000)
    if isinstance(raw, int) and raw > 0:
        return raw
    raise ValueError("invalid timestamp")


def normalized_observations(export, symbol, asset_class):
    """Use collector observation time, never historical publication time, for features."""
    rows = export.get("observations") or []
    by_identity = {}
    ignored = {"mismatched_asset": 0, "invalid": 0, "duplicate": 0}
    for row in rows:
        if not isinstance(row, dict):
            ignored["invalid"] += 1
            continue
        if row.get("asset") != symbol or row.get("asset_class") != asset_class:
            ignored["mismatched_asset"] += 1
            continue
        source, event = row.get("source"), row.get("event_id")
        if source not in SOURCES or not isinstance(event, str) or not event:
            continue
        try:
            observed = timestamp_ms(row["observed_at"])
            published = timestamp_ms(row["published_at"])
            if published > observed:
                raise ValueError("future publication")
        except (ValueError, KeyError, TypeError, OverflowError):
            ignored["invalid"] += 1
            continue
        key = (source, event)
        if key in by_identity:
            ignored["duplicate"] += 1
            if observed >= by_identity[key]["observed_ms"]:
                continue
        metrics = row.get("sample_metrics") if source == "social" else None
        if metrics is not None:
            if (not isinstance(metrics, dict) or
                metrics.get("provider") not in ("bluesky_search", "bluesky_monitored_accounts") or
                metrics.get("coverage") not in (
                    "bounded_search_sample_not_platform_total",
                    "bounded_monitored_accounts_not_platform_total"
                ) or
                any(type(metrics.get(k)) is not int or not 0 <= metrics[k] <= (
                    100 if metrics["provider"] == "bluesky_search" else 3000)
                    for k in ("sampled_posts", "sampled_unique_authors")) or
                metrics["sampled_unique_authors"] > metrics["sampled_posts"]):
                ignored["invalid"] += 1
                continue
        by_identity[key] = {
            "source": source, "event_id": event, "observed_ms": observed,
            "sample_metrics": metrics,
            # Existing source direction is a research heuristic, not measured sentiment.
        }
    return sorted(by_identity.values(), key=lambda x: x["observed_ms"]), ignored


def build(candles_export, intelligence_export, horizons=(300, 3600)):
    seconds = candles_export.get("seconds")
    if seconds not in (60, 300, 900):
        raise ValueError("supported candle intervals: 60, 300 and 900 seconds")
    symbol = candles_export.get("symbol")
    asset_class = candles_export.get("asset_class", "crypto")
    if not symbol or asset_class not in ("crypto", "stock", "forex"):
        raise ValueError("unsupported market identity")
    rows = candles_export.get("candles") or []
    if len(rows) < 25:
        raise ValueError("at least 25 candles required")
    source_names = set()
    for row in rows:
        if row.get("symbol") != symbol or row.get("asset_class", asset_class) != asset_class or row.get("seconds") != seconds:
            raise ValueError("mixed market or timeframe")
        source_names.add(row.get("source"))
    if len(source_names) != 1 or not next(iter(source_names)):
        raise ValueError("mixed or missing price source")
    bars = sorted(rows, key=lambda x: x["ts"])
    starts = [timestamp_ms(r["ts"]) for r in bars]
    if len(set(starts)) != len(starts):
        raise ValueError("duplicate candle timestamps")
    for r in bars:
        if any(type(r.get(k)) not in (int, float) for k in ("open", "high", "low", "close", "volume")):
            raise ValueError("invalid candle numeric field")
        from math import isfinite
        if any(not isfinite(r[k]) for k in ("open", "high", "low", "close", "volume")):
            raise ValueError("nonfinite candle")
        if min(r["open"], r["high"], r["low"], r["close"]) <= 0 or r["volume"] < 0:
            raise ValueError("invalid candle values")
        if r["low"] > min(r["open"], r["close"]) or r["high"] < max(r["open"], r["close"]):
            raise ValueError("invalid OHLC")
    observations, ignored = normalized_observations(intelligence_export, symbol, asset_class)
    event_times = {source: [o["observed_ms"] for o in observations if o["source"] == source] for source in SOURCES}
    social_snapshots = [o for o in observations if o["source"] == "social" and o.get("sample_metrics")]
    snapshot_times = [o["observed_ms"] for o in social_snapshots]
    interval_ms = seconds * 1000
    horizons = tuple(horizons)
    if not horizons or any(type(h) is not int or h < seconds or h % seconds or h not in HORIZONS for h in horizons):
        raise ValueError("horizons must be supported exact multiples of candle interval")
    outputs = []
    # A bar timestamp is its OPEN; its data becomes available at the CLOSE.
    for i in range(20, len(bars)-1):
        if any(starts[k+1] - starts[k] != interval_ms for k in range(i-19, i+1)):
            continue
        decision_ms = starts[i] + interval_ms
        # The next-bar opening price is a transparent execution proxy.
        for h in horizons:
            offset = h // seconds
            if i + offset >= len(bars):
                continue
            if any(starts[k+1] - starts[k] != interval_ms for k in range(i, i+offset)):
                continue
            entry = bars[i+1]["open"]
            future = bars[i+offset]["close"]
            features = {
                "close_return_1bar": bars[i]["close"] / bars[i-1]["close"] - 1,
                "close_return_5bar": bars[i]["close"] / bars[i-5]["close"] - 1,
                "volume_ratio_5bar": bars[i]["volume"] / max(1., sum(b["volume"] for b in bars[i-4:i+1])/5),
            }
            for source in ("news", "social"):
                times = event_times[source]
                upto = bisect.bisect_right(times, decision_ms)
                one_hour = bisect.bisect_right(times, decision_ms-WINDOW_MS)
                two_hours = bisect.bisect_right(times, decision_ms-2*WINDOW_MS)
                current = upto - one_hour
                prior = one_hour - two_hours
                features[source+"_observations_last_hour"] = current
                features[source+"_observations_prior_hour"] = prior
                features[source+"_observation_change"] = current-prior
            # Explicitly NULL when no provider has supplied auditable distinct
            # author counts or text-sentiment analysis.
            features["social_unique_authors"] = None
            features["social_sampled_posts"] = None
            features["social_sampled_previous_hour_posts"] = None
            features["social_sampled_post_change"] = None
            features["social_sample_provider"] = None
            features["social_sample_age_seconds"] = None
            latest_snapshot_idx = bisect.bisect_right(snapshot_times, decision_ms) - 1
            if latest_snapshot_idx >= 0:
                snap = social_snapshots[latest_snapshot_idx]
                age = decision_ms - snap["observed_ms"]
                # Stale snapshots must be unknown, not fabricated zeros.
                if 0 <= age <= WINDOW_MS:
                    metrics = snap["sample_metrics"]
                    features["social_sampled_posts"] = metrics["sampled_posts"]
                    features["social_unique_authors"] = metrics["sampled_unique_authors"]
                    features["social_sample_provider"] = metrics["provider"]
                    features["social_sample_age_seconds"] = age / 1000.
                    previous = metrics.get("previous_hour_posts")
                    if type(previous) is int and 0 <= previous <= 100:
                        features["social_sampled_previous_hour_posts"] = previous
                        features["social_sampled_post_change"] = metrics["sampled_posts"] - previous
            features["social_sentiment"] = None
            features["news_sentiment"] = None
            outputs.append({
                "symbol": symbol, "asset_class": asset_class, "price_source": next(iter(source_names)),
                "seconds": seconds, "decision_ms": decision_ms,
                "entry_ms": starts[i+1], "label_end_ms": starts[i+offset]+interval_ms,
                "horizon_seconds": h, "features": features,
                "label_up": int(future > entry),
                "future_return_proxy": future / entry - 1,
                "entry_price_proxy": entry, "exit_price_proxy": future,
                "research_only": True,
            })
    return {
        "status": "research_only_untrained", "market": symbol,
        "price_source": next(iter(source_names)), "observation_count": len(observations),
        "ignored_observations": ignored, "rows": outputs,
        "limitations": [
            "news/social counts are collector observations, not total mentions",
            "Bluesky counts and verified sentiment unavailable in legacy records",
            "events use collection observation time; no backdating to publish time",
            "entry/exit use proxies, not broker execution or non-overlapping trades",
            "5s and 30s horizons require genuine 5s candles and are unavailable with current owner export",
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--candles", required=True)
    parser.add_argument("--intelligence", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--horizons", default="300,3600", help="Comma-separated seconds")
    args = parser.parse_args()
    result = build(json.loads(Path(args.candles).read_text()),
                   json.loads(Path(args.intelligence).read_text()),
                   tuple(int(h) for h in args.horizons.split(",")))
    Path(args.output).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"rows": len(result["rows"]), "status": result["status"]}))
