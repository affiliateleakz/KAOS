"""Offline tests for the Market Intelligence scanner core (no network, no Mongo)."""
from datetime import datetime, timedelta, timezone

import pytest

import kaos_market_intel as mi

BASE = 1_700_000_000_000
MINUTE = 60_000


def bar(i, *, open_=100.0, close=100.0, high=None, low=None, volume=10.0, step=MINUTE):
    return {"ts": BASE + i * step, "open": open_, "high": high if high is not None else max(open_, close),
            "low": low if low is not None else min(open_, close), "close": close, "volume": volume}


def flat_bars(count=25, price=100.0, volume=10.0):
    return [bar(i, open_=price, close=price, high=price + 0.2, low=price - 0.2, volume=volume)
            for i in range(count)]


def now_after(bars, seconds=60):
    return datetime.fromtimestamp(bars[-1]["ts"] / 1000, tz=timezone.utc) + timedelta(seconds=seconds)


def test_validate_candles_rejects_unordered_duplicates_and_bad_prices():
    with pytest.raises(ValueError):
        mi.validate_candles([bar(1), bar(0)])
    with pytest.raises(ValueError):
        mi.validate_candles([bar(1), bar(1)])
    with pytest.raises(ValueError):
        mi.validate_candles([{"ts": 1, "open": 1, "high": 1, "low": 2, "close": 1}])
    with pytest.raises(ValueError):
        mi.validate_candles([{"ts": 1, "open": 1, "high": 1, "low": 1, "close": 0}])
    with pytest.raises(ValueError):
        mi.validate_candles([{"ts": 1, "open": 1, "high": 1, "low": 1, "close": 1, "volume": -3}])


def test_requires_enough_completed_bars():
    with pytest.raises(mi.InsufficientData):
        mi.technical_row("BTC-USD", flat_bars(10), asset_class="crypto", interval_seconds=60)


def test_breakout_and_volume_structure_are_reported_with_bar_close_as_of():
    bars = flat_bars(25)
    bars.append(bar(25, open_=100.1, close=102.0, high=102.2, low=100.0, volume=40.0))
    row = mi.technical_row("BTC-USD", bars, asset_class="crypto", interval_seconds=60, now=now_after(bars))
    codes = {s["code"] for s in row["signals"]}
    assert {"BREAKOUT_20", "UNUSUAL_VOLUME", "MOMENTUM_UP"} <= codes
    assert row["structure"] == "breakout"
    assert row["volume_ratio_20"] == pytest.approx(4.0, rel=1e-6)
    # as_of is the close of the last bar (open time + interval), not its open time.
    assert row["as_of"] == datetime.fromtimestamp((bars[-1]["ts"] + MINUTE) / 1000, tz=timezone.utc).isoformat()
    assert row["research_only"] is True
    assert row["score_type"] == "heuristic_attention_rank_not_probability"
    assert len(row["sparkline"]) == min(30, len(bars)) and row["sparkline"][-1] == 102.0


def test_trend_needs_fifty_bars_and_is_never_guessed():
    short = flat_bars(40)
    row = mi.technical_row("SPY", short, asset_class="stock", interval_seconds=60, now=now_after(short))
    assert row["trend"] == "insufficient_history"
    assert "TREND_UP" not in {s["code"] for s in row["signals"]}

    rising = [bar(i, open_=100 + i, close=101 + i, high=101.5 + i, low=99.5 + i) for i in range(60)]
    up = mi.technical_row("SPY", rising, asset_class="stock", interval_seconds=60, now=now_after(rising))
    assert up["trend"] == "up"
    assert "TREND_UP" in {s["code"] for s in up["signals"]}

    falling = [bar(i, open_=160 - i, close=159 - i, high=160.5 - i, low=158.5 - i) for i in range(60)]
    down = mi.technical_row("SPY", falling, asset_class="stock", interval_seconds=60, now=now_after(falling))
    assert down["trend"] == "down"


def test_failed_breakout_is_distinct_from_breakout():
    bars = flat_bars(25)
    bars.append(bar(25, open_=100.0, close=100.1, high=104.0, low=99.9, volume=12.0))
    row = mi.technical_row("ETH-USD", bars, asset_class="crypto", interval_seconds=60, now=now_after(bars))
    assert row["structure"] == "failed_breakout"
    assert "FAILED_BREAKOUT" in {s["code"] for s in row["signals"]}
    assert "BREAKOUT_20" not in {s["code"] for s in row["signals"]}


def test_scan_markets_reports_errors_instead_of_inventing_rows():
    good = flat_bars(25) + [bar(25, open_=100.1, close=102.0, high=102.2, low=100.0, volume=20.0)]
    result = mi.scan_markets(
        [("BTC-USD", good), ("ETH-USD", None, "Market data provider unreachable"), ("SOL-USD", flat_bars(3))],
        asset_class="crypto", interval_seconds=60, now=now_after(good))
    assert [r["symbol"] for r in result["rows"]] == ["BTC-USD"]
    reasons = {e["symbol"]: e["reason"] for e in result["errors"]}
    assert "unreachable" in reasons["ETH-USD"]
    assert "completed bars" in reasons["SOL-USD"]


def social(asset, i, *, minutes_ago, direction="neutral", event="bsky-search", strength=0.2):
    ts = (datetime(2026, 10, 18, 12, tzinfo=timezone.utc) - timedelta(minutes=minutes_ago)).isoformat()
    return {"asset": asset, "asset_class": "stock", "source": "social", "direction": direction,
            "strength": strength, "event_id": f"{event}:{asset}:{i}", "observed_at": ts,
            "published_at": ts, "source_url": f"https://bsky.app/profile/x/post/{i}",
            "summary": "sample"}


def test_social_activity_counts_ingested_observations_and_flags_acceleration():
    now = datetime(2026, 10, 18, 12, tzinfo=timezone.utc)
    observations = (
        [social("AAA", i, minutes_ago=5) for i in range(4)]
        + [social("AAA", i, minutes_ago=70) for i in range(1)]
        + [social("BBB", i, minutes_ago=5) for i in range(1)]
        + [{"asset": "CCC", "asset_class": "stock", "source": "news", "direction": "bullish",
            "event_id": "gdelt:1", "observed_at": now.isoformat(), "published_at": now.isoformat(),
            "source_url": "https://example.com", "strength": 0.9}]
    )
    result = mi.social_activity(observations, now=now)
    assert result["window_minutes"] == 60
    rows = {r["asset"]: r for r in result["rows"]}
    assert set(rows) == {"AAA", "BBB"}  # non-social observations are never mixed in
    assert rows["AAA"]["mentions_current_window"] == 4
    assert rows["AAA"]["mentions_prior_window"] == 1
    assert rows["AAA"]["velocity"] == "new" or rows["AAA"]["velocity"] == "rising"
    assert rows["BBB"]["velocity"] == "new"
    assert rows["AAA"]["providers"] == ["bsky-search"]
    assert rows["AAA"]["coverage"] == "ingested_observations_only_not_platform_wide"
    assert rows["AAA"]["mention_change_pct"] == 300.0
    assert result["counts_meaning"].startswith("Distinct stored observations")


def test_social_activity_rejects_unknown_windows_and_skips_bad_timestamps():
    now = datetime(2026, 10, 18, 12, tzinfo=timezone.utc)
    with pytest.raises(ValueError):
        mi.social_activity([], now=now, window_minutes=5)
    result = mi.social_activity([{"source": "social", "asset": "AAA", "event_id": "x:1",
                                  "observed_at": "not-a-time"}], now=now)
    assert result["rows"] == []
    assert result["skipped_records"] == 1


def test_options_research_parses_occ_metadata_and_refuses_to_invent_greeks():
    now = datetime(2026, 10, 18, 15, tzinfo=timezone.utc)
    expiry = now.strftime("%y%m%d")
    observations = [{
        "asset": f"SPY{expiry}C00500000", "asset_class": "option", "source": "options_flow",
        "direction": "neutral", "strength": 0.4, "event_id": "option-volume-rise:0:SPY:x",
        "observed_at": now.isoformat(), "published_at": now.isoformat(),
        "source_url": "https://docs.tradier.com/reference", "summary": "volume grew",
    }]
    result = mi.options_research(observations, now=now, underlying="SPY")
    assert result["matched"] == 1
    row = result["rows"][0]
    assert row["root"] == "SPY" and row["option_type"] == "call"
    assert row["same_day_expiration"] is True
    assert "delta" in result["metrics_unavailable"]
    assert result["coverage"] == "ingested_snapshots_only_not_market_wide_flow"

    empty = mi.options_research([], now=now, underlying="SPY")
    assert empty["rows"] == [] and empty["matched"] == 0


def test_options_research_filters_by_underlying_root():
    now = datetime(2026, 10, 18, 15, tzinfo=timezone.utc)
    expiry = now.strftime("%y%m%d")
    observations = [{
        "asset": f"AAPL{expiry}P00200000", "asset_class": "option", "source": "options_flow",
        "event_id": "option-volume-rise:0:AAPL:x", "observed_at": now.isoformat(),
        "published_at": now.isoformat(), "source_url": "https://docs.tradier.com", "summary": "",
    }]
    assert mi.options_research(observations, now=now, underlying="SPY")["rows"] == []
    assert len(mi.options_research(observations, now=now, underlying="AAPL")["rows"]) == 1


def crypto_row(symbol="BTC-USD", price=101.0, signals=None):
    return {"symbol": symbol, "last_close": price, "as_of": "2026-10-18T12:00:00+00:00",
            "signals": signals if signals is not None else [{"code": "BREAKOUT_20", "evidence": "closed above"}]}


def test_alert_matches_cover_each_supported_kind():
    crypto = [crypto_row()]
    social_rows = [{"asset": "AAA", "velocity": "rising", "mentions_current_window": 6,
                    "mentions_prior_window": 1, "latest_published_at": "2026-10-18T12:00:00+00:00"}]

    hit = mi.alert_matches({"id": "a1", "kind": "price_above", "symbol": "BTC-USD", "threshold": 100}, crypto_rows=crypto)
    assert hit["triggered"] is True and "at or above" in hit["reason"]
    miss = mi.alert_matches({"id": "a1", "kind": "price_above", "symbol": "BTC-USD", "threshold": 105}, crypto_rows=crypto)
    assert miss["triggered"] is False
    low = mi.alert_matches({"id": "a1", "kind": "price_below", "symbol": "BTC-USD", "threshold": 105}, crypto_rows=crypto)
    assert low["triggered"] is True
    assert mi.alert_matches({"id": "a2", "kind": "breakout_20"}, crypto_rows=crypto)["triggered"] is True
    assert mi.alert_matches({"id": "a3", "kind": "unusual_volume"}, crypto_rows=crypto)["triggered"] is False
    assert mi.alert_matches({"id": "a4", "kind": "social_velocity", "symbol": "AAA"},
                            social_rows=social_rows)["triggered"] is True
    assert mi.alert_matches({"id": "a5", "kind": "signal", "signal_code": "TREND_UP"},
                            crypto_rows=crypto)["triggered"] is False
    assert mi.alert_matches({"id": "a6", "kind": "unknown"})["triggered"] is False
    assert mi.alert_matches({"id": "a7", "kind": "price_above"})["triggered"] is False
