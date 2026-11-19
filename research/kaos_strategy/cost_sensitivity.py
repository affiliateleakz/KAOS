"""Does the edge survive real dealing costs?

The study charges 0.02 ATR per side, which is generous for a 5m FX candle. Spread plus
slippage on a retail feed is routinely 0.05-0.20 ATR. This re-runs the frozen
configuration at several cost levels and reports the pooled out-of-sample result, so the
breakeven cost is visible instead of assumed.

Run:  PYTHONPATH=. python3 cost_sensitivity.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

import data
from backtest import metrics, simulate_entries
from portability import FROZEN
from study import BASKET, SPLIT, asset_class, prepare, pulse_entries
from strategy import DEFAULT

OUT = Path(__file__).with_name("out")
COSTS = (0.0, 0.02, 0.05, 0.10, 0.20, 0.35)


def main():
    OUT.mkdir(exist_ok=True)
    cache = []
    for asset, tf in BASKET:
        df = data.load(asset, tf)
        n = len(df)
        cut = int(n * SPLIT)
        _, reg, sig, atr = prepare(df, DEFAULT)
        cache.append((asset, tf, asset_class(asset), df.iloc[cut:].reset_index(drop=True),
                      pulse_entries(sig, reg, cut, n), atr))

    rows = []
    for cost in COSTS:
        kept = []
        for asset, tf, cls, frame, entries, atr in cache:
            tr = simulate_entries(frame, entries, atr, FROZEN["tp"], FROZEN["sl"],
                                  FROZEN["bars"], cost, "pulse")
            if tr.empty:
                continue
            tr = tr.assign(asset=asset, tf=tf, cls=cls)
            kept.append(tr)
        if not kept:
            continue
        all_tr = pd.concat(kept, ignore_index=True)
        pnl = all_tr["pnl_atr"].to_numpy()
        wins = all_tr["outcome"].isin(["tp", "tp_gap"])
        losses = all_tr["outcome"].isin(["sl", "sl_gap"])
        gw, gl = pnl[pnl > 0].sum(), -pnl[pnl < 0].sum()
        row = {"cost_per_side_atr": cost, "n": int(len(all_tr)),
               "wr": float(wins.sum() / max((wins | losses).sum(), 1)),
               "exp": float(pnl.mean()), "total_atr": float(pnl.sum()),
               "pf": float(gw / gl) if gl else float("inf"),
               "positive_pairs": int(sum(
                   1 for _, g in all_tr.groupby("asset") if g["pnl_atr"].mean() > 0))}
        for cls in ("crypto", "fx", "equity"):
            sub = all_tr[all_tr["cls"] == cls]["pnl_atr"].to_numpy()
            row[f"exp_{cls}"] = float(sub.mean()) if len(sub) else float("nan")
        rows.append(row)
        print(f"cost {cost:.2f} ATR/side  n={row['n']:5d}  WR {row['wr']:.3f}  "
              f"exp {row['exp']:+.4f}  PF {row['pf']:.3f}  "
              f"crypto {row['exp_crypto']:+.3f}  fx {row['exp_fx']:+.3f}  eq {row['exp_equity']:+.3f}")
    pd.DataFrame(rows).to_csv(OUT / "cost_sensitivity.csv", index=False)
    (OUT / "cost_sensitivity.json").write_text(json.dumps(rows, indent=2))
    print(f"\nwrote {OUT}/cost_sensitivity.csv")


if __name__ == "__main__":
    main()
