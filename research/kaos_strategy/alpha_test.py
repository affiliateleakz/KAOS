"""Does any KAOS entry rule carry directional information?

Win rate is not evidence of edge, because a bracket geometry fixes the win rate of a
coin flip. This script therefore measures, for every entry variant, the mean signed
forward return in ATR units:

    alpha_h = mean( side * (close[t+h] - open[t+1]) / atr[t] )   over all signals

with a t-statistic. A rule with t > 2 has information; a rule with t ~ 0 cannot beat
its own barrier parity no matter which target/stop pair is chosen.
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

import data
from strategy import DEFAULT, Params, indicators, regime


def variants(ind: pd.DataFrame, p: Params) -> dict[str, np.ndarray]:
    c = ind["close"].to_numpy()
    o = ind["open"].to_numpy()
    h = ind["high"].to_numpy()
    lo = ind["low"].to_numpy()
    z = ind["z"].to_numpy()
    rsi = ind["rsi"].to_numpy()
    er = ind["er"].to_numpy()
    reg = regime(ind, p)
    atr = ind["atr"].to_numpy()
    ok = np.isfinite(atr) & (atr > 0)

    out = {}
    out["pulse"] = np.where((reg == 0) & (z <= -p.z_entry) & (rsi <= p.rsi_pulse), 1,
                            np.where((reg == 0) & (z >= p.z_entry) & (rsi >= 100 - p.rsi_pulse), -1, 0))
    out["drive"] = np.where((reg == 1) & (lo <= ind["ema_fast"].to_numpy()) & (c > ind["ema_fast"].to_numpy()), 1,
                            np.where((reg == -1) & (h >= ind["ema_fast"].to_numpy()) & (c < ind["ema_fast"].to_numpy()), -1, 0))
    out["mr_raw"] = np.where(z <= -1.5, 1, np.where(z >= 1.5, -1, 0))
    out["mom_raw"] = np.where(z >= 1.5, 1, np.where(z <= -1.5, -1, 0))
    hi20 = pd.Series(h).rolling(20).max().to_numpy()
    lo20 = pd.Series(lo).rolling(20).min().to_numpy()
    out["breakout"] = np.where(c > np.roll(hi20, 1), 1, np.where(c < np.roll(lo20, 1), -1, 0))
    out["er_mom"] = np.where((er >= 0.45) & (c > ind["ema_slow"].to_numpy()), 1,
                             np.where((er >= 0.45) & (c < ind["ema_slow"].to_numpy()), -1, 0))
    for k in out:
        out[k] = np.where(ok, out[k], 0).astype(np.int8)
    return out


def alpha(ind: pd.DataFrame, sig: np.ndarray, horizons=(1, 3, 6, 12, 24)) -> pd.DataFrame:
    o = ind["open"].to_numpy(float)
    c = ind["close"].to_numpy(float)
    atr = ind["atr"].to_numpy(float)
    n = len(ind)
    rows = []
    idx = np.flatnonzero(sig != 0)
    for h in horizons:
        usable = idx[(idx + h + 1) < n]
        if len(usable) < 30:
            continue
        fwd = sig[usable] * (c[usable + h] - o[usable + 1]) / atr[usable]
        rows.append({"h": h, "n": len(usable), "alpha_atr": float(fwd.mean()),
                     "t": float(fwd.mean() / (fwd.std(ddof=1) / np.sqrt(len(usable)))),
                     "hit": float((fwd > 0).mean())})
    return pd.DataFrame(rows)


def main(datasets):
    for asset, tf in datasets:
        df = data.load(asset, tf)
        ind = indicators(df, DEFAULT)
        print(f"\n=== {asset} {tf}  bars={len(df)}")
        for name, sig in variants(ind, DEFAULT).items():
            a = alpha(ind, sig)
            if a.empty:
                continue
            best = a.iloc[a["t"].abs().idxmax()]
            print(f"  {name:9s} n={int(a['n'].iloc[0]):5d} "
                  f"alpha@h{int(best['h'])!s}={best['alpha_atr']:+.4f}ATR t={best['t']:+.2f} "
                  f"hit={best['hit']:.3f}")


if __name__ == "__main__":
    pairs = [("BTCUSD", "5m"), ("BTCUSD", "1h"), ("AAPL", "5m"), ("SPY", "15m"), ("EURUSD", "5m")]
    main(pairs)
