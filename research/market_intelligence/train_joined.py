"""Offline KAOS news/social + candle model evaluation, research only.

Requires numpy, scikit-learn. Input is output of build_dataset.py.
Runs separate models for each horizon, with purged chronological boundaries.
No orders, model registry writes, deployment or trading authorization.
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import accuracy_score, balanced_accuracy_score, log_loss

NUMERIC_FEATURES = (
    "close_return_1bar", "close_return_5bar", "volume_ratio_5bar",
    "news_observations_last_hour", "news_observations_prior_hour",
    "news_observation_change", "social_observations_last_hour",
    "social_observations_prior_hour", "social_observation_change",
    "social_sampled_posts", "social_unique_authors",
    "social_sampled_previous_hour_posts", "social_sampled_post_change",
    "social_sample_age_seconds",
)


def evaluate(dataset, horizon_seconds, cost_bps=10.0):
    if type(horizon_seconds) is not int or horizon_seconds <= 0:
        raise ValueError("horizon_seconds must be positive integer")
    if not isinstance(cost_bps, (int, float)) or not math.isfinite(cost_bps) or cost_bps < 0:
        raise ValueError("cost_bps must be nonnegative finite value")
    if dataset.get("status") != "research_only_untrained":
        raise ValueError("unexpected training dataset")
    rows = sorted((r for r in dataset.get("rows", [])
                   if r.get("horizon_seconds") == horizon_seconds),
                  key=lambda r: r["decision_ms"])
    if len(rows) < 180:
        raise ValueError("at least 180 labeled samples required for horizon")
    identity = {(r.get("symbol"), r.get("asset_class"), r.get("price_source"),
                 r.get("seconds"), r.get("horizon_seconds")) for r in rows}
    if len(identity) != 1:
        raise ValueError("mixed market/source/timeframe/horizon; evaluate separately")
    decisions = np.asarray([r["decision_ms"] for r in rows], dtype=np.int64)
    ends = np.asarray([r["label_end_ms"] for r in rows], dtype=np.int64)
    if len(np.unique(decisions)) != len(decisions) or np.any(ends <= decisions):
        raise ValueError("duplicate decisions or invalid forward label interval")
    if np.any(np.diff(decisions) <= 0):
        raise ValueError("decision timestamps not increasing")
    features = []
    for r in rows:
        if r.get("research_only") is not True or not isinstance(r.get("features"), dict):
            raise ValueError("non-research or missing features")
        vector = []
        for key in NUMERIC_FEATURES:
            value = r["features"].get(key)
            if value is None:
                vector.append(float("nan"))
            elif type(value) in (float, int) and math.isfinite(value):
                vector.append(float(value))
            else:
                raise ValueError("invalid numeric feature")
        features.append(vector)
    X = np.asarray(features, dtype=float)
    y = np.asarray([r["label_up"] for r in rows], dtype=np.int64)
    if np.any((y != 0) & (y != 1)):
        raise ValueError("invalid labels")
    returns = np.asarray([r["future_return_proxy"] for r in rows], dtype=float)
    if not np.isfinite(returns).all():
        raise ValueError("invalid forward returns")
    n = len(rows)
    va_start, te_start = int(.6*n), int(.8*n)
    # Purge all labels crossing the next split's first decision.
    tr = np.flatnonzero(ends[:va_start] < decisions[va_start])
    va = np.flatnonzero((np.arange(n) >= va_start) &
                       (np.arange(n) < te_start) &
                       (ends < decisions[te_start]))
    te = np.arange(te_start, n)
    if min(len(tr), len(va), len(te)) < 25:
        raise ValueError("too few examples after split purging")
    if len(np.unique(y[tr])) != 2:
        raise ValueError("training labels contain only one direction")
    # Scikit-learn histogram binning can fail on columns with no observed
    # training values. Exclude only columns entirely missing in the TRAIN split.
    # Never inspect validation/test features to decide this selection.
    usable = np.isfinite(X[tr]).any(axis=0)
    if not np.any(usable):
        raise ValueError("no observed training features available")
    X = X[:, usable]
    model = HistGradientBoostingClassifier(
        max_iter=80, max_leaf_nodes=7, learning_rate=.04,
        l2_regularization=5.0, random_state=42,
    )
    model.fit(X[tr], y[tr])
    val_p = model.predict_proba(X[va])[:, 1]
    candidates = (.55, .60, .65, .70)

    def proxy(p, index, threshold):
        side = np.where(p >= threshold, 1, np.where(p <= 1-threshold, -1, 0))
        selected = side != 0
        net = side[selected] * returns[index][selected] - cost_bps / 10000.0
        return {
            "signal_count": int(np.sum(selected)),
            "coverage": float(np.mean(selected)),
            "net_mean_return_proxy": float(np.mean(net)) if len(net) else None,
            "net_win_rate_proxy": float(np.mean(net > 0)) if len(net) else None,
        }

    ranked = [(t, proxy(val_p, va, t)) for t in candidates]
    valid = [pair for pair in ranked if pair[1]["signal_count"] >= 10]
    # Do not force a trading result if no candidate has enough validation data.
    threshold = max(valid, key=lambda p: (p[1]["net_mean_return_proxy"], -p[0]))[0] if valid else None
    test_p = model.predict_proba(X[te])[:, 1]
    return {
        "status": "research_only_not_deployed",
        "symbol": rows[0]["symbol"],
        "asset_class": rows[0]["asset_class"],
        "price_source": rows[0]["price_source"],
        "seconds": rows[0]["seconds"],
        "horizon_seconds": horizon_seconds,
        "split_samples": {"train": int(len(tr)), "validation": int(len(va)), "test": int(len(te))},
        "train_last_label_ms": int(ends[tr[-1]]),
        "validation_first_decision_ms": int(decisions[va[0]]),
        "validation_last_label_ms": int(ends[va[-1]]),
        "test_first_decision_ms": int(decisions[te[0]]),
        "test_accuracy": float(accuracy_score(y[te], test_p >= .5)),
        "test_balanced_accuracy": float(balanced_accuracy_score(y[te], test_p >= .5)),
        "test_log_loss": float(log_loss(y[te], test_p, labels=[0, 1])),
        "test_majority_class_baseline_accuracy": float(max(np.mean(y[te]), 1-np.mean(y[te]))),
        "selected_validation_threshold": threshold,
        "test_trade_proxies": proxy(test_p, te, threshold) if threshold is not None else None,
        "feature_names": [name for name, keep in zip(NUMERIC_FEATURES, usable) if keep],
        "excluded_unobserved_features": [name for name, keep in zip(NUMERIC_FEATURES, usable) if not keep],
        "limits": [
            "experimental directional classifier; not calibrated winning probabilities",
            "sampled public social posts do not represent total mentions",
            "no verified sentiment and legacy sparse history may limit feature usefulness",
            "no non-overlap enforcement, bid/ask fills, execution latency or short borrow",
            "cost_bps is a simple proxy, not a broker-specific execution simulation",
            "threshold selected using validation only; test evaluated once",
            "not investment advice, live orders or published performance",
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--horizon-seconds", type=int, default=300)
    parser.add_argument("--cost-bps", type=float, default=10.)
    args = parser.parse_args()
    report = evaluate(json.loads(Path(args.input).read_text()), args.horizon_seconds, args.cost_bps)
    Path(args.output).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "test_accuracy": report["test_accuracy"]}))
