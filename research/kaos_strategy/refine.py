"""Can the entry filter pay for the spread?

The frozen geometry already clears the 65% win rate, but at 0.05 ATR per side the pooled
expectancy is negative. Two principled filters might fix that, and only two are tested
here so the search stays small:

* a deeper stretch requirement (z and RSI must be more extreme), and
* a volatility floor (skip bars whose ATR is below its own 200-bar median), because cost
  is paid in ATR and dead ranges are where a 3-ATR target is unreachable.

Variants are compared on the TRAIN slice only. The winner is then run once on the TEST
slice. Five comparisons on train, one confirmation on test.

Run:  PYTHONPATH=. python3 refine.py
"""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

import data
from backtest import metrics, simulate_entries
from portability import FROZEN
from study import BASKET, SPLIT, prepare, pulse_entries
from strategy import DEFAULT

OUT = Path(__file__).with_name("out")
COST = 0.05
VARIANTS = {
    "baseline":        {"z": 1.0, "rsi": 42.0, "vol": False},
    "deeper":          {"z": 1.5, "rsi": 38.0, "vol": False},
    "deepest":         {"z": 2.0, "rsi": 35.0, "vol": False},
    "vol_floor":       {"z": 1.0, "rsi": 42.0, "vol": True},
    "deep_vol_floor":  {"z": 1.5, "rsi": 38.0, "vol": True},
}


def entries_for(asset, tf, variant, lo, hi):
    df = data.load(asset, tf)
    p = replace(DEFAULT, z_entry=variant["z"], rsi_pulse=variant["rsi"])
    ind, reg, sig, atr = prepare(df, p)
    if variant["vol"]:
        ref = pd.Series(atr).rolling(200, min_periods=50).median().to_numpy()
        sig = np.where(np.isfinite(ref) & (atr >= ref), sig, 0).astype(np.int8)
    return df, atr, pulse_entries(sig, reg, lo, hi)


def evaluate(variant, lo_frac, hi_frac):
    frames = []
    for asset, tf in BASKET:
        df = data.load(asset, tf)
        n = len(df)
        lo, hi = int(n * lo_frac), int(n * hi_frac)
        _, atr, entries = entries_for(asset, tf, variant, lo, hi)
        tr = simulate_entries(df.iloc[lo:hi].reset_index(drop=True), entries, atr,
                              FROZEN["tp"], FROZEN["sl"], FROZEN["bars"], COST, "pulse")
        if not tr.empty:
            frames.append(tr.assign(asset=asset, tf=tf))
    if not frames:
        return None, pd.DataFrame()
    all_tr = pd.concat(frames, ignore_index=True)
    m = metrics(all_tr, FROZEN["tp"], FROZEN["sl"])
    per_asset = all_tr.groupby("asset")["pnl_atr"].mean()
    return {"n": m["n"], "wr": round(m["wr"], 4), "excess_pp": round(m["excess_pp"], 2),
            "exp": round(m["expectancy_atr"], 4), "pf": round(m["pf"], 3),
            "positive_assets": int((per_asset > 0).sum()), "assets": int(len(per_asset))}, all_tr


def main():
    OUT.mkdir(exist_ok=True)
    train, test = {}, {}
    for name, v in VARIANTS.items():
        tr, _ = evaluate(v, 0.0, SPLIT)
        train[name] = tr
        print(f"train  {name:16s} " + (f"n={tr['n']:4d} WR {tr['wr']:.3f} exp {tr['exp']:+.4f} "
                                       f"PF {tr['pf']:.3f} assets+ {tr['positive_assets']}/{tr['assets']}"
                                       if tr else "no trades"))
    best = max((k for k in train if train[k]), key=lambda k: train[k]["exp"])
    print(f"\nselected on train by expectancy: {best}")
    for name in (best, "baseline"):
        te, trades = evaluate(VARIANTS[name], SPLIT, 1.0)
        test[name] = te
        print(f"test   {name:16s} n={te['n']:4d} WR {te['wr']:.3f} excess {te['excess_pp']:+.2f}pp "
              f"exp {te['exp']:+.4f} PF {te['pf']:.3f} assets+ {te['positive_assets']}/{te['assets']}")
        if name == best:
            trades.to_csv(OUT / "refined_trades.csv", index=False)
    (OUT / "refine.json").write_text(json.dumps({"cost_per_side_atr": COST, "train": train,
                                                 "test": test, "selected": best}, indent=2))
    print(f"\nwrote {OUT}/refine.json")


if __name__ == "__main__":
    main()
