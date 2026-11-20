"""Research-only candle classifier. No live orders, deployments, or model promotion.

Input: JSON from /api/v1/owner/candles/export.
Usage: python research/ai_training/train.py --input candles.json --output report.json
Requires numpy and scikit-learn.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import accuracy_score, balanced_accuracy_score, log_loss

LOOKBACK = 20


def prepare(export, horizon=1):
    if type(horizon) is not int or not 1 <= horizon <= 60:
        raise ValueError("horizon must be in bars 1..60")
    seconds = export.get("seconds")
    if seconds not in (60, 300, 900):
        raise ValueError("only 1m/5m/15m closed candles supported")
    rows = export.get("candles") or []
    if len(rows) < 160:
        raise ValueError("at least 160 archived candles required")
    if any(r.get("source") != rows[0].get("source") or
           r.get("symbol") != export.get("symbol") or
           r.get("seconds") != seconds for r in rows) or not rows[0].get("source"):
        raise ValueError("mixed source, symbol, or timeframe")
    rows = sorted(rows, key=lambda r: r["ts"])
    ts = np.array([r["ts"] for r in rows], dtype=np.int64)
    prices = np.array([[r[k] for k in ("open", "high", "low", "close", "volume")]
                       for r in rows], dtype=float)
    if not np.isfinite(prices).all() or np.any(prices[:, :4] <= 0) or np.any(prices[:, 4] < 0):
        raise ValueError("invalid candle prices or volume")
    op, hi, lo, cl, vol = prices.T
    if np.any(lo > np.minimum(op, cl)) or np.any(hi < np.maximum(op, cl)) or np.any(hi < lo):
        raise ValueError("invalid OHLC")
    if np.any(np.diff(ts) <= 0):
        raise ValueError("duplicate candle timestamps")
    gaps = np.diff(ts) != seconds * 1000
    X, y, entry, exit_price, decision_ts, exit_ts = [], [], [], [], [], []
    for i in range(LOOKBACK - 1, len(rows) - horizon):
        if gaps[i - LOOKBACK + 1:i + horizon].any():
            continue
        price = cl[i]
        entry_price = op[i + 1]
        end_price = cl[i + horizon]
        features = [price / cl[i-j] - 1 for j in (1, 3, 5, 10)]
        features += [
            price / np.mean(cl[i-4:i+1]) - 1,
            price / np.mean(cl[i-19:i+1]) - 1,
            (hi[i]-lo[i]) / price, (cl[i]-op[i]) / price,
            (hi[i]-max(op[i], cl[i])) / price,
            (min(op[i], cl[i])-lo[i]) / price,
            vol[i] / max(1., float(np.mean(vol[i-19:i+1])))
        ]
        X.append(features)
        y.append(int(end_price > entry_price))
        entry.append(entry_price)
        exit_price.append(end_price)
        decision_ts.append(ts[i])
        exit_ts.append(ts[i+horizon])
    if len(y) < 100:
        raise ValueError("not enough contiguous labeled examples")
    return tuple(np.asarray(x) for x in (X, y, entry, exit_price, decision_ts, exit_ts))


def purged_splits(decision_ts, exit_ts):
    n = len(decision_ts)
    v, t = int(.60*n), int(.80*n)
    train = np.flatnonzero(exit_ts < decision_ts[v])
    validation = np.flatnonzero((np.arange(n) >= v) & (exit_ts < decision_ts[t]))
    test = np.arange(t, n)
    if min(len(train), len(validation), len(test)) < 20:
        raise ValueError("insufficient examples after purging")
    return train, validation, test


def positions(prob, entry, exit_price, threshold, cost_bps):
    direction = np.where(prob >= threshold, 1, np.where(prob <= 1-threshold, -1, 0))
    chosen = np.flatnonzero(direction)
    gross = direction[chosen] * (exit_price[chosen]/entry[chosen]-1)
    net = gross - cost_bps / 10000.
    return {
        "signals": int(len(chosen)),
        "coverage": float(len(chosen)/len(direction)),
        "mean_net_return_proxy": float(np.mean(net)) if len(net) else None,
        "net_win_rate_proxy": float(np.mean(net > 0)) if len(net) else None,
        "overlapping_signals_possible": True,
    }


def train(export, horizon=1, cost_bps=10.):
    if not np.isfinite(cost_bps) or cost_bps < 0:
        raise ValueError("invalid cost_bps")
    X, y, entry, end, decisions, exits = prepare(export, horizon)
    tr, va, te = purged_splits(decisions, exits)
    if len(set(y[tr])) != 2:
        raise ValueError("training requires both directions")
    model = HistGradientBoostingClassifier(max_iter=80, max_leaf_nodes=7,
                                           learning_rate=.04, l2_regularization=5.,
                                           random_state=42)
    model.fit(X[tr], y[tr])
    val_prob = model.predict_proba(X[va])[:, 1]
    candidates = (.50, .55, .60, .65, .70)
    def objective(t):
        scored = positions(val_prob, entry[va], end[va], t, cost_bps)
        return scored["mean_net_return_proxy"] if scored["signals"] >= 10 else float("-inf")
    threshold = max(candidates, key=lambda t: (objective(t), -t))
    test_prob = model.predict_proba(X[te])[:, 1]
    return {
        "status": "research_only_not_deployed",
        "symbol": export["symbol"], "source": export["candles"][0]["source"],
        "seconds": export["seconds"], "horizon_bars": horizon,
        "split_counts": {"train": len(tr), "validation": len(va), "test": len(te)},
        "split_times": {
            "train_last_label_ms": int(exits[tr[-1]]),
            "validation_first_decision_ms": int(decisions[va[0]]),
            "validation_last_label_ms": int(exits[va[-1]]),
            "test_first_decision_ms": int(decisions[te[0]])
        },
        "validation_selected_threshold": threshold,
        "test_accuracy": float(accuracy_score(y[te], test_prob >= .5)),
        "test_balanced_accuracy": float(balanced_accuracy_score(y[te], test_prob >= .5)),
        "test_log_loss": float(log_loss(y[te], test_prob, labels=[0, 1])),
        "test_majority_baseline_accuracy": float(max(np.mean(y[te]), 1-np.mean(y[te]))),
        "test_positions": positions(test_prob, entry[te], end[te], threshold, cost_bps),
        "limitations": ["single source/market/horizon", "indicative next-open fills",
                        "no order book or stop/target execution model", "no overlapping position constraint",
                        "not a broker profit claim", "no trading authority"]
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--horizon-bars", type=int, default=1)
    parser.add_argument("--cost-bps", type=float, default=10.)
    args = parser.parse_args()
    result = train(json.loads(Path(args.input).read_text()), args.horizon_bars, args.cost_bps)
    Path(args.output).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"test_accuracy": result["test_accuracy"], "status": result["status"]}))
