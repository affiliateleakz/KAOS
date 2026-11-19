"""Win rate is a property of the bracket, not of the signal.

Sweeps target/stop multiples on one fixed entry engine and prints, per geometry, the
win rate next to its barrier parity and the resulting expectancy. A row with a 70% win
rate and a negative expectancy is the honest picture of most "high win rate" systems.
"""
from __future__ import annotations

import itertools

import numpy as np

import data
from backtest import simulate, metrics
from strategy import DEFAULT, indicators, regime, signal_series

TPS = (0.25, 0.4, 0.6, 0.8, 1.2, 1.8, 2.5)
SLS = (0.6, 0.9, 1.2, 1.8, 2.5, 3.5, 5.0)


def sweep(asset: str, tf: str, cost=0.02, max_bars=12):
    df = data.load(asset, tf)
    ind = indicators(df, DEFAULT)
    reg = regime(ind, DEFAULT)
    sig = signal_series(ind, DEFAULT)
    atr = ind["atr"].to_numpy()
    sig = np.where(reg == 0, sig, 0).astype(np.int8)   # PULSE only, isolates the geometry

    rows = []
    for tp, sl in itertools.product(TPS, SLS):
        tr = simulate(df, sig, atr, DEFAULT, tp, sl, max_bars, cost, "pulse")
        m = metrics(tr, tp, sl)
        if m.get("n", 0) < 40:
            continue
        rows.append({"tp": tp, "sl": sl, "n": m["n"], "wr": m["wr"], "parity": m["parity"],
                     "excess": m["excess_pp"], "exp": m["expectancy_atr"], "pf": m["pf"]})
    if not rows:
        print(f"{asset} {tf}: no geometry produced enough trades")
        return
    rows.sort(key=lambda r: r["exp"], reverse=True)
    print(f"\n=== {asset} {tf}: top 6 by expectancy (cost {cost} ATR/side)")
    print("   tp    sl     n     WR    parity  excess   exp_atr   PF")
    for r in rows[:6]:
        print(f"  {r['tp']:4.2f}  {r['sl']:4.2f} {r['n']:5d}  {r['wr']:.3f}  {r['parity']:.3f}  "
              f"{r['excess']:+6.2f}  {r['exp']:+.4f}  {r['pf']:.2f}")
    hi = [r for r in rows if r["wr"] >= 0.65]
    print(f"  geometries with WR>=65%: {len(hi)}; of those with exp>0: {sum(1 for r in hi if r['exp'] > 0)}")
    if hi:
        best = max(hi, key=lambda r: r["exp"])
        print(f"  best WR>=65% row: tp={best['tp']} sl={best['sl']} WR={best['wr']:.3f} "
              f"parity={best['parity']:.3f} exp={best['exp']:+.4f}")


if __name__ == "__main__":
    for pair in [("BTCUSD", "5m"), ("SOLUSD", "5m"), ("SPY", "15m"), ("AAPL", "5m"), ("EURUSD", "5m")]:
        sweep(*pair)
