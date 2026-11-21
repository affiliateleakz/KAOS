"""Paired, leakage-safe experiment: OHLC versus OHLC + one evidence source.

Strictly research-only. Uses identical eligible candles, chronological purged
splits, and real availability times. No deployment or trade authority.
"""
import bisect
import hashlib
import json
import math
from datetime import datetime, timezone, timedelta

from kaos_r2_ai_lab import make_samples, _split, _score, _evaluate, FEATURES
from kaos_ai_evidence_features import make_feature_snapshot
from kaos_opportunity import SOURCES, utc
from kaos_source_health import SOURCE_AGE_MINUTES

MIN_PAIRED = 250
EPOCHS = 160


def _iso(ts):
    return datetime.fromtimestamp(ts / 1000, timezone.utc)


def _fit(rows, names):
    n = len(names)
    mean = [sum(r["x"][j] for r in rows) / len(rows) for j in range(n)]
    std = [max(1e-5, math.sqrt(sum((r["x"][j]-mean[j])**2
                                  for r in rows)/len(rows))) for j in range(n)]
    weights = [0.0] * n
    bias = 0.0
    for epoch in range(EPOCHS):
        grad = [0.0] * n
        grad_bias = 0.0
        for row in rows:
            x = [max(-8, min(8, (v-mean[j])/std[j]))
                 for j, v in enumerate(row["x"])]
            logit = max(-30, min(30, sum(weights[j]*x[j]
                                       for j in range(n))+bias))
            probability = 1/(1+math.exp(-logit))
            error = probability-row["y"]
            grad_bias += error
            for j in range(n):
                grad[j] += error*x[j]
        rate = .12/(1+epoch/100)
        for j in range(n):
            weights[j] -= rate*(grad[j]/len(rows)+.01*weights[j])
        bias -= rate*grad_bias/len(rows)
    return {"features": list(names), "weights": weights,
            "mean": mean, "std": std, "bias": bias,
            "schema": "kaos_evidence_ablation_logistic_v1"}


def _metrics(rows, model):
    if not rows:
        return {"samples": 0, "signals": 0, "directional_accuracy": None,
                "brier": None, "coverage": None, "signal_accuracy": None}
    probabilities = [_score(row, model) for row in rows]
    decided = [(p >= .6 or p <= .4, (p >= .6) == bool(row["y"]))
               for row, p in zip(rows, probabilities)]
    triggers = [ok for active, ok in decided if active]
    return {
        "samples": len(rows), "signals": len(triggers),
        "coverage": round(len(triggers)/len(rows), 4),
        "signal_accuracy": round(sum(triggers)/len(triggers), 4) if triggers else None,
        "directional_accuracy": round(sum((p >= .5) == bool(row["y"])
                                          for row, p in zip(rows, probabilities))/len(rows), 4),
        "brier": round(sum((p-row["y"])**2
                            for row, p in zip(rows, probabilities))/len(rows), 6),
    }


def compare_models(rows, observations, *, symbol, asset_class, seconds=60,
                   horizon=4, source_category="news"):
    """Return holdout comparison, without usable model weights or action signals."""
    if source_category not in SOURCES:
        raise ValueError("Invalid intelligence feature family")
    if not isinstance(observations, list) or len(observations) > 5000:
        raise ValueError("Too many intelligence records")
    if not isinstance(rows, list) or len(rows) > 5000:
        raise ValueError("Too many candles")
    samples = make_samples(rows, seconds, horizon)
    # Index by first observed availability; then verify published_at and
    # source/event timestamps within make_feature_snapshot.
    eligible = []
    for record in observations:
        if not isinstance(record, dict) or record.get("source") != source_category:
            continue
        try:
            observed = utc(record["observed_at"])
        except (ValueError, TypeError, KeyError):
            continue
        eligible.append((observed, record))
    eligible.sort(key=lambda item: item[0])
    seen_at = [at for at, _ in eligible]
    freshness = SOURCE_AGE_MINUTES.get(source_category, 60) * 60
    paired = []
    seen_samples = 0
    for s in samples:
        # Candle opens at ts; only after close may its technical inputs be used.
        decision = _iso(s["ts"] + seconds*1000)
        left = bisect.bisect_left(seen_at, decision-timedelta(seconds=freshness))
        right = bisect.bisect_right(seen_at, decision)
        candidates = [record for _, record in eligible[left:right][-100:]]
        snapshot = make_feature_snapshot(
            symbol=symbol, asset_class=asset_class,
            decision_at=decision, observations=candidates,
            candle_source=rows[0].get("source"), candle_end_at=decision)
        category = snapshot["categories"][source_category]
        if category["state"] != "fresh":
            continue
        up = category["bullish_evidence"] or 0.0
        down = category["bearish_evidence"] or 0.0
        # Only compare where the selected source has actual directional
        # evidence; no missing/neutral evidence treated as a bearish zero.
        if not (up or down):
            continue
        paired.append({**s, "extra": [up-down, min(4, category["independent_providers"])]})
    report = {
        "schema": "kaos_ai_paired_evidence_comparison_v1",
        "symbol": symbol, "asset_class": asset_class,
        "source_category": source_category, "seconds": seconds,
        "horizon_bars": horizon, "candle_samples": len(samples),
        "paired_samples": len(paired),
        "excluded_no_relevant_point_in_time_evidence": len(samples)-len(paired),
        "execution_enabled": False, "research_only": True,
        "no_order_authority": True, "promotable": False,
    }
    if len(paired) < MIN_PAIRED:
        return {**report, "status": "insufficient_paired_history",
                "required_paired_samples": MIN_PAIRED}
    baseline = [{**r, "x": r["x"][:]} for r in paired]
    enhanced = [{**r, "x": r["x"]+r["extra"]} for r in paired]
    b_train, b_val, b_test = _split(baseline, horizon)
    e_train, e_val, e_test = _split(enhanced, horizon)
    if (len(b_train)<100 or len(b_val)<30 or len(b_test)<30
        or len({r["y"] for r in b_train})<2 or
        [r["ts"] for r in b_test] != [r["ts"] for r in e_test]):
        return {**report, "status": "insufficient_purged_split"}
    b_model = _fit(b_train, FEATURES)
    e_model = _fit(e_train, (*FEATURES, source_category+"_direction", source_category+"_providers"))
    b_test_metrics = _metrics(b_test, b_model)
    e_test_metrics = _metrics(e_test, e_model)
    b_val_metrics = _metrics(b_val, b_model)
    e_val_metrics = _metrics(e_val, e_model)
    # Evaluation only: no weight export, no model registry and no
    # authority to deploy. Lower Brier is better calibrated on this test.
    return {
        **report, "status": "comparison_complete_unvalidated",
        "train_samples": len(b_train),
        "validation_samples": len(b_val),
        "test_samples": len(b_test),
        "test_start_ts": b_test[0]["ts"],
        "test_end_ts": b_test[-1]["settlement_ts"],
        "validation": {"candle_only": b_val_metrics,
                       "candle_plus_evidence": e_val_metrics},
        "holdout_test": {"candle_only": b_test_metrics,
                         "candle_plus_evidence": e_test_metrics},
        "brier_delta_enhanced_minus_candle": round(
            e_test_metrics["brier"]-b_test_metrics["brier"], 6),
        "outperforms_baseline_on_brier": e_test_metrics["brier"] < b_test_metrics["brier"],
        "warnings": [
            "Selected data is conditional on intelligence coverage; not all market hours.",
            "Brier comparison is not a trade win rate; costs, payouts and execution excluded.",
            "This experiment may be selection-biased; needs independent walk-forward validation.",
            "No model is saved, promoted, authorized to signal or trade."
        ],
    }
