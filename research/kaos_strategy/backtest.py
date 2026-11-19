"""Backtest engine for the KAOS Strategy.

Rules that keep the result honest:

* A signal is evaluated on a closed bar and filled at the NEXT bar's open, so no
  decision ever uses information from the bar it trades.
* If a bar contains both the target and the stop, the STOP is assumed to fill first.
  This is the pessimistic convention; optimistic fills inflate win rate by 5-15 pp.
* A gap through the stop fills at the open, i.e. worse than the stop price.
* Trades never overlap, so the win rate is not double-counted across simultaneous
  signals on the same instrument.
* Cost is charged in ATR units on both entry and exit.

The headline check is not the win rate itself but the win rate minus barrier parity.
For a driftless random walk with target a and stop b, P(target first) = b/(a+b), so a
strategy showing 65% wins with a 0.8/1.2 bracket (parity 60%) has 5 pp of real edge,
while 70% wins with a 0.3/3.0 bracket (parity 91%) is simply losing money.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from strategy import DEFAULT, Params, indicators, regime, signal_series


def simulate(df: pd.DataFrame, sig: np.ndarray, atr: np.ndarray, p: Params,
             tp_mult: float, sl_mult: float, max_bars: int, cost_atr: float,
             engine: str = "pulse") -> pd.DataFrame:
    """Walk signals forward with bracket exits. Returns one row per trade."""
    n = len(df)
    entries = [(i, int(sig[i])) for i in range(n - 1) if int(sig[i]) != 0]
    return simulate_entries(df, entries, atr, tp_mult, sl_mult, max_bars, cost_atr, engine)


def simulate_entries(df: pd.DataFrame, entries, atr: np.ndarray,
                     tp_mult: float, sl_mult: float, max_bars: int, cost_atr: float,
                     engine: str = "pulse") -> pd.DataFrame:
    """Simulate an explicit `(bar_index, side)` entry list.

    Sharing this path with the signal engine is what makes the placebo control fair:
    a random-entry run is scored by byte-identical exit logic and costs.
    """
    o = df["open"].to_numpy(float)
    h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float)
    c = df["close"].to_numpy(float)
    ts = df["ts"].to_numpy()
    n = len(df)

    trades = []
    free_from = 0
    for i, side in sorted(entries):
        if side == 0 or i < free_from or i >= n - 1 or not np.isfinite(atr[i]) or atr[i] <= 0:
            continue
        entry_i = i + 1
        entry = o[entry_i]
        a = float(atr[i])
        if side > 0:
            tp, sl = entry + tp_mult * a, entry - sl_mult * a
        else:
            tp, sl = entry - tp_mult * a, entry + sl_mult * a

        exit_price = None
        outcome = "time"
        j = entry_i
        while j < min(entry_i + max_bars, n):
            if side > 0:
                if o[j] <= sl:
                    exit_price, outcome = o[j], "sl_gap"
                    break
                if o[j] >= tp:
                    exit_price, outcome = o[j], "tp_gap"
                    break
                hit_sl, hit_tp = l[j] <= sl, h[j] >= tp
            else:
                if o[j] >= sl:
                    exit_price, outcome = o[j], "sl_gap"
                    break
                if o[j] <= tp:
                    exit_price, outcome = o[j], "tp_gap"
                    break
                hit_sl, hit_tp = h[j] >= sl, l[j] <= tp
            if hit_sl and hit_tp:
                exit_price, outcome = sl, "sl"
                break
            if hit_sl:
                exit_price, outcome = sl, "sl"
                break
            if hit_tp:
                exit_price, outcome = tp, "tp"
                break
            j += 1
        if exit_price is None:
            exit_price = c[min(entry_i + max_bars, n) - 1]
            j = min(entry_i + max_bars, n) - 1

        pnl_atr = side * (exit_price - entry) / a - 2 * cost_atr
        trades.append({"engine": engine, "entry_ts": ts[entry_i], "exit_ts": ts[min(j, n - 1)], "side": side,
                       "entry": entry, "exit": exit_price, "bars": j - entry_i + 1,
                       "atr": a, "pnl_atr": pnl_atr, "outcome": outcome})
        free_from = j + 1

    return pd.DataFrame(trades)


def metrics(trades: pd.DataFrame, tp_mult: float, sl_mult: float) -> dict:
    if trades.empty:
        return {"n": 0}
    pnl = trades["pnl_atr"].to_numpy()
    wins = int((trades["outcome"].isin(["tp", "tp_gap"])).sum())
    losses = int((trades["outcome"].isin(["sl", "sl_gap"])).sum())
    decided = wins + losses
    wr = wins / decided if decided else float("nan")
    parity = sl_mult / (tp_mult + sl_mult)
    equity = np.cumsum(pnl)
    peak = np.maximum.accumulate(np.r_[0.0, equity])[1:]
    dd = float(np.max(peak - equity)) if len(equity) else 0.0
    gross_win = float(pnl[pnl > 0].sum())
    gross_loss = float(-pnl[pnl < 0].sum())
    z = ((wins - decided * parity) / math.sqrt(decided * parity * (1 - parity))) if decided else float("nan")
    return {"n": len(trades), "wins": wins, "losses": losses, "wr": wr, "parity": parity,
            "excess_pp": (wr - parity) * 100, "z_vs_parity": z,
            "expectancy_atr": float(pnl.mean()), "total_atr": float(pnl.sum()),
            "pf": (gross_win / gross_loss) if gross_loss else float("inf"),
            "max_dd_atr": dd, "avg_bars": float(trades["bars"].mean()),
            # decided-only win rate can look better than reality when many trades time out,
            # so the share of time exits and the all-trade win rate are reported too
            "time_share": float((trades["outcome"] == "time").mean()),
            "pnl_wr": float((pnl > 0).mean())}


def run(df: pd.DataFrame, p: Params = DEFAULT, tp_mult: float | None = None,
        sl_mult: float | None = None, max_bars: int | None = None,
        cost_atr: float = 0.02, start: int = 0, end: int | None = None) -> tuple[pd.DataFrame, dict]:
    """Slice, then indicate → signal → simulate → score."""
    sl = df.iloc[start:end].reset_index(drop=True)
    ind = indicators(sl, p)
    sig = signal_series(ind, p)
    atr = ind["atr"].to_numpy()
    reg = regime(ind, p)

    # PULSE and DRIVE carry different bracket geometry; route each signal accordingly.
    tp_mult = p.tp_atr if tp_mult is None else tp_mult
    sl_mult = p.sl_atr if sl_mult is None else sl_mult
    max_bars = p.max_bars if max_bars is None else max_bars

    frames = []
    if np.any((sig != 0) & (reg == 0)):
        frames.append(simulate(sl, np.where(reg == 0, sig, 0), atr, p, tp_mult, sl_mult, max_bars, cost_atr, "pulse"))
    if np.any((sig != 0) & (reg != 0)) and p.mode in ("drive", "both"):
        frames.append(simulate(sl, np.where(reg != 0, sig, 0), atr, p,
                               p.dr_tp_atr, p.dr_sl_atr, p.dr_max_bars, cost_atr, "drive"))
    frames = [f for f in frames if not f.empty]
    if not frames:
        return pd.DataFrame(), {"n": 0}
    trades = pd.concat(frames).sort_values("entry_ts").reset_index(drop=True)
    m = metrics(trades, tp_mult, sl_mult)
    m["pulse_n"] = int((trades["engine"] == "pulse").sum())
    m["drive_n"] = int((trades["engine"] == "drive").sum())
    return trades, m


def walk_forward(df: pd.DataFrame, p: Params = DEFAULT, split: float = 0.6, **kw):
    """Chronological split: parameters are never chosen on the test slice."""
    cut = int(len(df) * split)
    tr_trades, tr = run(df, p, start=0, end=cut, **kw)
    te_trades, te = run(df, p, start=cut, end=None, **kw)
    return {"train": tr, "test": te, "train_trades": tr_trades, "test_trades": te_trades}


def bootstrap_wr(trades: pd.DataFrame, n_boot: int = 2000, seed: int = 7) -> tuple[float, float]:
    """95% CI for the win rate of decided trades."""
    if trades.empty:
        return (float("nan"), float("nan"))
    won = trades["outcome"].isin(["tp", "tp_gap"]).to_numpy().astype(int)
    lost = trades["outcome"].isin(["sl", "sl_gap"]).to_numpy().astype(int)
    sample = np.r_[won[won == 1], lost[lost == 1]]
    if len(sample) < 10:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    means = rng.choice(sample, size=(n_boot, len(sample)), replace=True).mean(axis=1)
    return float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))
