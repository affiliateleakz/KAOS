"""KAOS Strategy - final walk-forward study.

Protocol (fixed before looking at any test number):

1.  Every dataset is split chronologically 60/40. Nothing from the second slice is used
    to choose a parameter.
2.  On the TRAIN slice only, a geometry grid (target ATR, stop ATR, bar expiry) is swept
    for the PULSE engine. The selected geometry is the one with the highest expectancy
    among those that clear the user's win-rate target of 65% and a minimum trade count.
3.  That single geometry is then applied unchanged to the TEST slice together with the
    DRIVE engine at its default brackets.
4.  Each test slice is also run with a placebo control: the same number of entries, at
    random bars inside the same slice, with the same long/short mix, scored by the same
    exit code and the same costs. Anything the real signal cannot beat is geometry.

Run:  PYTHONPATH=. python3 study.py
"""
from __future__ import annotations

import json
import math
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

import data
from backtest import bootstrap_wr, metrics, simulate_entries
from strategy import DEFAULT, Params, indicators, regime, signal_series

OUT = Path(__file__).with_name("out")
SPLIT = 0.6
COST_ATR = 0.02          # per side, in ATR units
MIN_TRAIN_TRADES = 40
WR_TARGET = 0.65
WARMUP = 60

TP_GRID = (0.5, 0.8, 1.2, 1.8, 2.5, 3.0)
SL_GRID = (1.2, 1.8, 2.5, 3.5, 5.0)
BARS_GRID = (12, 24, 48)

BASKET = [
    (a, tf) for a in ("BTCUSD", "ETHUSD", "SOLUSD") for tf in ("5m", "15m", "1h", "4h")
] + [
    (a, tf) for a in ("BTCUSD", "ETHUSD") for tf in ("1m",)
] + [
    (a, tf) for a in ("EURUSD", "GBPUSD", "USDJPY") for tf in ("5m", "15m", "1h", "4h")
] + [
    (a, tf) for a in ("AAPL", "NVDA", "SPY", "QQQ") for tf in ("5m", "15m", "1h", "4h")
]


def asset_class(asset: str) -> str:
    if asset.endswith("USD") and asset[:3] in {"BTC", "ETH", "SOL", "XRP"}:
        return "crypto"
    if asset.endswith("USD"):
        return "fx"
    return "equity"


def prepare(df: pd.DataFrame, p: Params):
    ind = indicators(df, p)
    reg = regime(ind, p)
    sig = signal_series(ind, p)
    atr = ind["atr"].to_numpy()
    return ind, reg, sig, atr


def pulse_entries(sig: np.ndarray, reg: np.ndarray, lo: int, hi: int):
    """Entry list in SLICE coordinates (0 = first bar of df.iloc[lo:hi])."""
    idx = np.arange(lo, hi - 1)
    keep = (reg[idx] == 0) & (sig[idx] != 0)
    return [(int(i) - lo, int(sig[i])) for i in idx[keep]]


def drive_entries(sig: np.ndarray, reg: np.ndarray, lo: int, hi: int):
    idx = np.arange(lo, hi - 1)
    keep = (reg[idx] != 0) & (sig[idx] != 0)
    return [(int(i) - lo, int(sig[i])) for i in idx[keep]]


def calibrate(df, atr, sig, reg, lo, hi, p: Params):
    """Sweep geometry on the train slice; keep the best that clears the WR target."""
    entries = pulse_entries(sig, reg, lo, hi)
    rows = []
    for tp in TP_GRID:
        for sl in SL_GRID:
            for bars in BARS_GRID:
                tr = simulate_entries(df.iloc[lo:hi].reset_index(drop=True), entries, atr,
                                      tp, sl, bars, COST_ATR, "pulse")
                if tr.empty:
                    continue
                m = metrics(tr, tp, sl)
                if m["n"] < MIN_TRAIN_TRADES:
                    continue
                rows.append({"tp": tp, "sl": sl, "bars": bars, **m})
    if not rows:
        return None, rows
    qualifying = [r for r in rows if r["wr"] >= WR_TARGET]
    pool = qualifying or rows
    best = max(pool, key=lambda r: (r["expectancy_atr"], r["excess_pp"]))
    return best, rows


def placebo(df, atr, lo, hi, n_entries: int, long_share: float, tp, sl, bars, seed=11):
    """Random entries, matched count and direction mix, same exit code and costs."""
    rng = np.random.default_rng(seed)
    candidates = np.arange(lo + WARMUP, hi - 1)
    candidates = candidates[np.isfinite(atr[candidates]) & (atr[candidates] > 0)]
    if len(candidates) == 0 or n_entries == 0:
        return pd.DataFrame()
    picks = rng.choice(candidates, size=min(n_entries, len(candidates)), replace=False)
    picks.sort()
    sides = np.where(rng.random(len(picks)) < long_share, 1, -1)
    entries = [(int(i) - lo, int(s)) for i, s in zip(picks, sides)]
    return simulate_entries(df.iloc[lo:hi].reset_index(drop=True), entries, atr,
                            tp, sl, bars, COST_ATR, "placebo")


def evaluate_pair(asset: str, tf: str):
    df = data.load(asset, tf)
    n = len(df)
    cut = int(n * SPLIT)
    ind, reg, sig, atr = prepare(df, DEFAULT)

    best, grid = calibrate(df, atr, sig, reg, 0, cut, DEFAULT)
    row = {"asset": asset, "tf": tf, "class": asset_class(asset), "bars": n,
           "train_bars": cut, "test_bars": n - cut}
    if best is None:
        row["status"] = "no_geometry"
        return row, None

    tp, sl, bars = best["tp"], best["sl"], best["bars"]
    row.update({"tp": tp, "sl": sl, "bars": bars,
                "train_wr": round(best["wr"], 4), "train_parity": round(best["parity"], 4),
                "train_exp": round(best["expectancy_atr"], 4), "train_n": best["n"],
                "grid_size": len(grid),
                "train_geometries_above_target": sum(1 for r in grid if r["wr"] >= WR_TARGET)})

    # ---- out of sample, same geometry, no re-tuning
    te_entries = pulse_entries(sig, reg, cut, n)
    te = simulate_entries(df.iloc[cut:].reset_index(drop=True), te_entries, atr,
                          tp, sl, bars, COST_ATR, "pulse")
    tm = metrics(te, tp, sl) if not te.empty else {"n": 0}
    if tm.get("n", 0) >= 5:
        lo_ci, hi_ci = bootstrap_wr(te)
        row.update({"test_n": tm["n"], "test_wr": round(tm["wr"], 4),
                    "test_parity": round(tm["parity"], 4),
                    "test_excess_pp": round(tm["excess_pp"], 2),
                    "test_exp": round(tm["expectancy_atr"], 4),
                    "test_pf": round(tm["pf"], 3) if math.isfinite(tm["pf"]) else None,
                    "test_z": round(tm["z_vs_parity"], 2),
                    "test_wr_lo": round(lo_ci, 4), "test_wr_hi": round(hi_ci, 4),
                    "test_dd_atr": round(tm["max_dd_atr"], 2)})

        longs = sum(1 for _, s in te_entries if s > 0)
        share = longs / max(len(te_entries), 1)
        pl = placebo(df, atr, cut, n, len(te_entries), share, tp, sl, bars)
        pm = metrics(pl, tp, sl) if not pl.empty else {"n": 0}
        if pm.get("n", 0) >= 5:
            row.update({"placebo_n": pm["n"], "placebo_wr": round(pm["wr"], 4),
                        "placebo_exp": round(pm["expectancy_atr"], 4),
                        "lift_vs_placebo_pp": round((tm["wr"] - pm["wr"]) * 100, 2)})

    # ---- DRIVE engine on its default brackets, same split
    dr = simulate_entries(df.iloc[cut:].reset_index(drop=True),
                          drive_entries(sig, reg, cut, n), atr,
                          DEFAULT.dr_tp_atr, DEFAULT.dr_sl_atr, DEFAULT.dr_max_bars, COST_ATR, "drive")
    dm = metrics(dr, DEFAULT.dr_tp_atr, DEFAULT.dr_sl_atr) if not dr.empty else {"n": 0}
    if dm.get("n", 0) >= 5:
        row.update({"drive_n": dm["n"], "drive_wr": round(dm["wr"], 4),
                    "drive_parity": round(dm["parity"], 4),
                    "drive_exp": round(dm["expectancy_atr"], 4)})

    return row, te


def main():
    OUT.mkdir(exist_ok=True)
    rows, curves = [], {}
    for asset, tf in BASKET:
        try:
            row, te = evaluate_pair(asset, tf)
        except Exception as exc:  # a missing dataset must not abort the study
            rows.append({"asset": asset, "tf": tf, "class": asset_class(asset),
                         "status": f"error: {exc}"})
            print(f"{asset:7s} {tf:4s} ERROR {exc}")
            continue
        rows.append(row)
        if te is not None and not te.empty:
            curves[f"{asset}_{tf}"] = list(np.cumsum(te["pnl_atr"].to_numpy()).round(4))
        if row.get("status") == "no_geometry":
            print(f"{asset:7s} {tf:4s} no geometry cleared the minimum trade count")
        else:
            print(f"{asset:7s} {tf:4s} tp={row['tp']:.1f} sl={row['sl']:.1f} b={row['bars']:2d} "
                  f"| train WR {row['train_wr']:.3f} | test WR {row.get('test_wr', float('nan')):.3f} "
                  f"parity {row.get('test_parity', float('nan')):.3f} "
                  f"exp {row.get('test_exp', float('nan')):+.3f} "
                  f"placebo {row.get('placebo_wr', float('nan')):.3f}")

    frame = pd.DataFrame(rows)
    frame.to_csv(OUT / "study.csv", index=False)
    (OUT / "study.json").write_text(json.dumps(rows, indent=2, default=str))
    (OUT / "equity_curves.json").write_text(json.dumps(curves))
    (OUT / "study.md").write_text(to_markdown(frame))
    print(f"\nwrote {OUT}/study.csv, study.md, study.json, equity_curves.json")


def to_markdown(f: pd.DataFrame) -> str:
    done = f[f["test_n"].notna()] if "test_n" in f.columns else f.iloc[0:0]
    lines = ["| Asset | TF | Class | Train WR | Test n | Test WR | Parity | Excess pp | Exp (ATR) | PF | Placebo WR | Lift pp |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for _, r in done.iterrows():
        lines.append(
            f"| {r['asset']} | {r['tf']} | {r['class']} | {r['train_wr']:.3f} | {int(r['test_n'])} | "
            f"{r['test_wr']:.3f} | {r['test_parity']:.3f} | {r['test_excess_pp']:+.2f} | "
            f"{r['test_exp']:+.4f} | {r['test_pf'] if r['test_pf'] is not None else 'inf'} | "
            f"{r.get('placebo_wr', float('nan')):.3f} | {r.get('lift_vs_placebo_pp', float('nan')):+.2f} |")
    if len(done):
        lines += ["",
                  f"Pairs evaluated: {len(done)}",
                  f"Mean test WR: {done['test_wr'].mean():.3f}",
                  f"Share with WR >= 65%: {(done['test_wr'] >= 0.65).mean():.3f}",
                  f"Mean excess over parity: {done['test_excess_pp'].mean():+.2f} pp",
                  f"Share with positive expectancy: {(done['test_exp'] > 0).mean():.3f}",
                  f"Mean lift over placebo: {done['lift_vs_placebo_pp'].mean():+.2f} pp"]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
