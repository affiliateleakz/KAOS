"""Portability test: one frozen parameter set, every market in the basket.

The study in `study.py` re-selects geometry on each dataset's train slice, which is
convenient but flatters the result. The real claim the user needs is different:

    "one rule set, no re-tuning, works on crypto, FX and equities from 1m to 4h"

So this test freezes the geometry BEFORE seeing any number - tp = 3.0 ATR, stop = 5.0 ATR,
expiry = 24 bars, PULSE only - and applies it unchanged to the out-of-sample slice of
every dataset. A neighbourhood grid is also printed so a single lucky cell cannot be
mistaken for robustness.

Run:  PYTHONPATH=. python3 portability.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

import data
from backtest import bootstrap_wr, metrics, simulate_entries
from study import BASKET, COST_ATR, SPLIT, asset_class, placebo, prepare, pulse_entries
from strategy import DEFAULT

OUT = Path(__file__).with_name("out")
FROZEN = {"tp": 3.0, "sl": 5.0, "bars": 24}
NEIGHBOURS_TP = (2.0, 2.5, 3.0, 3.5, 4.0)
NEIGHBOURS_SL = (3.5, 4.5, 5.0, 6.0)


def run_pair(asset: str, tf: str):
    df = data.load(asset, tf)
    n = len(df)
    cut = int(n * SPLIT)
    _, reg, sig, atr = prepare(df, DEFAULT)

    slice_df = df.iloc[cut:].reset_index(drop=True)
    entries = pulse_entries(sig, reg, cut, n)
    tr = simulate_entries(slice_df, entries, atr, FROZEN["tp"], FROZEN["sl"], FROZEN["bars"], COST_ATR, "pulse")
    m = metrics(tr, FROZEN["tp"], FROZEN["sl"]) if not tr.empty else {"n": 0}
    row = {"asset": asset, "tf": tf, "class": asset_class(asset), "signals": len(entries)}
    if m.get("n", 0) < 5:
        row["status"] = "too_few_trades"
        return row, None

    lo, hi = bootstrap_wr(tr)
    row.update({"n": m["n"], "wr": round(m["wr"], 4), "parity": round(m["parity"], 4),
                "excess_pp": round(m["excess_pp"], 2), "z": round(m["z_vs_parity"], 2),
                "exp": round(m["expectancy_atr"], 4), "total_atr": round(m["total_atr"], 2),
                "pf": round(m["pf"], 3) if np.isfinite(m["pf"]) else None,
                "pnl_wr": round(m["pnl_wr"], 4), "time_share": round(m["time_share"], 3),
                "wr_lo": round(lo, 4), "wr_hi": round(hi, 4), "dd_atr": round(m["max_dd_atr"], 2),
                "avg_bars": round(m["avg_bars"], 1)})

    longs = sum(1 for _, s in entries if s > 0)
    pl = placebo(df, atr, cut, n, len(entries), longs / max(len(entries), 1),
                 FROZEN["tp"], FROZEN["sl"], FROZEN["bars"])
    pm = metrics(pl, FROZEN["tp"], FROZEN["sl"]) if not pl.empty else {"n": 0}
    if pm.get("n", 0) >= 5:
        row.update({"placebo_n": pm["n"], "placebo_wr": round(pm["wr"], 4),
                    "placebo_exp": round(pm["expectancy_atr"], 4),
                    "lift_pp": round((m["wr"] - pm["wr"]) * 100, 2),
                    "exp_lift": round(m["expectancy_atr"] - pm["expectancy_atr"], 4)})
    return row, tr


def neighbourhood(asset: str, tf: str) -> list[dict]:
    df = data.load(asset, tf)
    n = len(df)
    cut = int(n * SPLIT)
    _, reg, sig, atr = prepare(df, DEFAULT)
    slice_df = df.iloc[cut:].reset_index(drop=True)
    entries = pulse_entries(sig, reg, cut, n)
    out = []
    for tp in NEIGHBOURS_TP:
        for sl in NEIGHBOURS_SL:
            tr = simulate_entries(slice_df, entries, atr, tp, sl, FROZEN["bars"], COST_ATR, "pulse")
            if tr.empty:
                continue
            m = metrics(tr, tp, sl)
            out.append({"asset": asset, "tf": tf, "tp": tp, "sl": sl, "n": m["n"],
                        "wr": round(m["wr"], 4), "exp": round(m["expectancy_atr"], 4)})
    return out


def main():
    OUT.mkdir(exist_ok=True)
    rows, curves, nb = [], {}, []
    focus = [("BTCUSD", "5m"), ("ETHUSD", "5m"), ("SOLUSD", "5m"), ("EURUSD", "5m"),
             ("GBPUSD", "5m"), ("USDJPY", "5m"), ("AAPL", "5m"), ("SPY", "15m")]
    for asset, tf in BASKET:
        try:
            row, tr = run_pair(asset, tf)
        except Exception as exc:
            rows.append({"asset": asset, "tf": tf, "class": asset_class(asset), "status": f"error: {exc}"})
            continue
        rows.append(row)
        if tr is not None and not tr.empty:
            curves[f"{asset}_{tf}"] = list(np.cumsum(tr["pnl_atr"].to_numpy()).round(4))
        if row.get("status"):
            print(f"{asset:7s} {tf:4s} {row['status']}")
        else:
            print(f"{asset:7s} {tf:4s} n={row['n']:4d} WR {row['wr']:.3f} (parity {row['parity']:.3f}) "
                  f"exp {row['exp']:+.3f} placebo {row.get('placebo_wr', float('nan')):.3f} "
                  f"time {row['time_share']:.2f}")
    for pair in focus:
        try:
            nb.extend(neighbourhood(*pair))
        except Exception:
            pass

    frame = pd.DataFrame(rows)
    frame.to_csv(OUT / "portability.csv", index=False)
    (OUT / "portability.json").write_text(json.dumps(rows, indent=2, default=str))
    (OUT / "portability_equity.json").write_text(json.dumps(curves))
    pd.DataFrame(nb).to_csv(OUT / "neighbourhood.csv", index=False)

    done = frame[frame.get("n").notna()] if "n" in frame.columns else frame.iloc[0:0]
    lines = ["| Asset | TF | Class | n | WR | Parity | Excess pp | Exp ATR | PF | All-trade WR | Time exits | Placebo WR | Lift pp |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for _, r in done.sort_values(["class", "asset", "tf"]).iterrows():
        lines.append(f"| {r['asset']} | {r['tf']} | {r['class']} | {int(r['n'])} | {r['wr']:.3f} | "
                     f"{r['parity']:.3f} | {r['excess_pp']:+.2f} | {r['exp']:+.4f} | "
                     f"{r['pf'] if r['pf'] is not None else 'inf'} | {r['pnl_wr']:.3f} | "
                     f"{r['time_share'] * 100:.0f}% | {r.get('placebo_wr', float('nan')):.3f} | "
                     f"{r.get('lift_pp', float('nan')):+.2f} |")
    if len(done):
        lines += ["",
                  f"Pairs: {len(done)} | mean WR {done['wr'].mean():.3f} | "
                  f"WR>=65% on {(done['wr'] >= 0.65).mean() * 100:.0f}% of pairs",
                  f"Mean excess over parity {done['excess_pp'].mean():+.2f} pp | "
                  f"positive expectancy on {(done['exp'] > 0).mean() * 100:.0f}% of pairs",
                  f"Mean lift over placebo {done['lift_pp'].mean():+.2f} pp"]
        by_class = done.groupby("class").agg(pairs=("wr", "size"), wr=("wr", "mean"),
                                             exp=("exp", "mean"), lift=("lift_pp", "mean"))
        lines += ["", "| Class | Pairs | Mean WR | Mean exp ATR | Mean lift pp |", "|---|---|---|---|---|"]
        for cls, r in by_class.iterrows():
            lines.append(f"| {cls} | {int(r['pairs'])} | {r['wr']:.3f} | {r['exp']:+.4f} | {r['lift']:+.2f} |")
    (OUT / "portability.md").write_text("\n".join(lines) + "\n")
    print("\n" + "\n".join(lines[-12:]))
    print(f"\nwrote {OUT}/portability.md, portability.csv, neighbourhood.csv")


if __name__ == "__main__":
    main()
