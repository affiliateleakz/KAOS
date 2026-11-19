"""Does a stricter deviation filter convert a weak edge into a high win rate?

For each dataset the mean-reversion entry is re-tested at increasing |z| thresholds.
Reported per bucket: signal count, forward alpha with t-stat, and the bracket win rate
next to its barrier parity.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import data
from backtest import simulate, metrics
from strategy import DEFAULT, indicators, regime


def bucket_study(asset: str, tf: str, thresholds=(1.0, 1.5, 2.0, 2.5, 3.0),
                 tp=0.8, sl=1.2, max_bars=12, cost=0.02):
    df = data.load(asset, tf)
    ind = indicators(df, DEFAULT)
    reg = regime(ind, DEFAULT)
    z = ind["z"].to_numpy()
    rsi = ind["rsi"].to_numpy()
    atr = ind["atr"].to_numpy()
    o = ind["open"].to_numpy(float)
    c = ind["close"].to_numpy(float)
    ok = np.isfinite(atr) & (atr > 0)

    print(f"\n=== {asset} {tf}  tp={tp} sl={sl} bars={max_bars} (parity {sl/(tp+sl):.3f})")
    print("  |z|>=  n_sig   alpha_h12   t      WR     parity  excess   exp_atr")
    for th in thresholds:
        long_ = (reg == 0) & (z <= -th) & (rsi <= 50) & ok
        short_ = (reg == 0) & (z >= th) & (rsi >= 50) & ok
        sig = np.where(long_, 1, np.where(short_, -1, 0)).astype(np.int8)
        idx = np.flatnonzero(sig != 0)
        idx = idx[(idx + 13) < len(ind)]
        if len(idx) < 30:
            print(f"  {th:4.1f}  {len(idx):6d}   (too few)")
            continue
        fwd = sig[idx] * (c[idx + 12] - o[idx + 1]) / atr[idx]
        t = fwd.mean() / (fwd.std(ddof=1) / np.sqrt(len(idx)))
        tr = simulate(df, sig, atr, DEFAULT, tp, sl, max_bars, cost, "pulse")
        m = metrics(tr, tp, sl) if not tr.empty else {"n": 0}
        if not m.get("n"):
            continue
        print(f"  {th:4.1f}  {len(idx):6d}  {fwd.mean():+0.4f}  {t:+5.2f}  "
              f"{m['wr']:.3f}  {m['parity']:.3f}  {m['excess_pp']:+6.2f}  {m['expectancy_atr']:+.4f}")


if __name__ == "__main__":
    for pair in [("BTCUSD", "5m"), ("SOLUSD", "5m"), ("SPY", "15m"), ("AAPL", "5m"),
                 ("EURUSD", "5m"), ("BTCUSD", "15m")]:
        bucket_study(*pair)
