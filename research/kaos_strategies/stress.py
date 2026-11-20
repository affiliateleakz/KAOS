"""Cost and payout stress.

A backtest that only survives at 0.02 ATR per side is not tradeable - real spreads on 5m crypto
or a 1m FX cross are wider than that at times. This re-scores each strategy at 0, 2, 5 and 10
basis points of ATR per side, and each binary rule at 60/80/92% payout.

    python stress.py    # writes out/STRESS.md
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

import core
import evaluate
import strategies  # noqa: F401

OUT = Path(__file__).resolve().parent / "out"
COSTS = (0.0, 0.02, 0.05, 0.10)
PAYOUTS = (0.60, 0.80, 0.92)


def bracket_pool(strategy, cost: float) -> pd.DataFrame:
    frames = []
    for _, _, _, df in evaluate.iter_pairs(strategy):
        _, sig = strategy.signal_fn(df, dict(strategy.params))
        cut = int(len(df) * 0.6)
        tr = evaluate.bracket_trades(df, sig, strategy.exit, cost, cut, len(df))
        if not tr.empty:
            frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def binary_pool(strategy) -> pd.DataFrame:
    frames = []
    for _, _, _, df in evaluate.iter_pairs(strategy):
        _, sig = strategy.signal_fn(df, dict(strategy.params))
        cut = int(len(df) * 0.6)
        tr = evaluate.expiry_trades(df, sig, int(strategy.exit.get("expiry_bars", 3)), cut, len(df))
        if not tr.empty:
            frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def main() -> None:
    OUT.mkdir(exist_ok=True)
    lines = ["| Strategy | " + " | ".join(f"cost {c:.3f} ATR/side" for c in COSTS) + " |",
             "|---" * (len(COSTS) + 1) + "|"]
    detail = {}
    for sid, strategy in core.REGISTRY.items():
        if strategy.signal_fn is None or strategy.mode != "bracket":
            continue
        cells, vals = [], {}
        for cost in COSTS:
            trades = bracket_pool(strategy, cost)
            m = evaluate.bracket_metrics(trades, strategy.exit["tp_atr"], strategy.exit["sl_atr"])
            vals[cost] = m
            cells.append(f"{m['expectancy_atr']:+.3f} (PF {m['pf']:.2f})" if m.get("n") else "-")
        detail[sid] = vals
        lines.append(f"| {strategy.name} | " + " | ".join(cells) + " |")

    binary_lines = ["| Strategy | " + " | ".join(f"payout {p:.0%}" for p in PAYOUTS) + " |",
                    "|---" * (len(PAYOUTS) + 1) + "|"]
    for sid, strategy in core.REGISTRY.items():
        if strategy.mode != "expiry":
            continue
        trades = binary_pool(strategy)
        if trades.empty:
            continue
        cells = []
        for payout in PAYOUTS:
            m = evaluate.expiry_metrics(trades, payout)
            be = 1 / (1 + payout)
            cells.append(f"{m['expectancy_atr']:+.3f} (WR {m['wr']:.1%} vs {be:.1%})")
        binary_lines.append(f"| {strategy.name} | " + " | ".join(cells) + " |")

    md = "\n".join([
        "# Cost and payout stress (out-of-sample)", "",
        "Expectancy per trade; PF = profit factor. Cost is charged on entry and exit.",
        "", *lines, "",
        "## Binary options", "",
        "Binary bets pay `payout` on a win and lose the stake on a loss, so break-even win rate is",
        "`1/(1+payout)`. A rule below that line loses money however it is staked.",
        "", *binary_lines, ""])
    (OUT / "STRESS.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
