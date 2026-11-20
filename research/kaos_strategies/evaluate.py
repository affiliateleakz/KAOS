"""Scoring engine for the strategy library.

Two execution models, one standard of proof:

    bracket  - target and stop in ATR multiples, evaluated with the v1 engine (next-open fill,
               stop wins ties, gaps fill worse, no overlapping trades, cost in ATR per side).
    expiry   - fixed bar expiry, direction only (binary options). Win = expiry close is on the
               trade's side of the entry. Scored against the payout break-even rate, not parity.

Every strategy is scored three ways on the same out-of-sample slice:

    1. the strategy itself
    2. barrier parity  - what a driftless walk would produce with the same brackets
    3. matched placebo - the same number of entries, same long/short mix, random bars

A strategy only earns a place in the library if it beats both 2 and 3 with a positive
expectancy after costs. Reusing the v1 simulate_entries path for the placebo is deliberate:
the control has to go through byte-identical exit logic or it isn't a control.
"""
from __future__ import annotations

import math
import os
from pathlib import Path

import numpy as np
import pandas as pd

import core
from core import Strategy
import backtest as v1bt

DATA_DIR = Path(__file__).resolve().parent.parent / "kaos_strategy" / "data"

# asset class -> (universe, timeframes available on disk)
UNIVERSE = {
    "crypto": (("BTCUSD", "ETHUSD", "SOLUSD", "XRPUSD"), ("1m", "5m", "15m", "1h", "4h")),
    "fx": (("EURUSD", "GBPUSD", "USDJPY", "AUDUSD"), ("5m", "15m", "1h", "4h")),
    "equity": (("AAPL", "MSFT", "NVDA", "SPY", "QQQ", "TSLA"), ("5m", "15m", "1h", "4h")),
    "binary": (("BTCUSD", "ETHUSD", "EURUSD", "AAPL"), ("1m", "5m")),
    "options": (("SPY", "QQQ"), ("1h",)),
}
OPTIONS_UNDERLYING_TF = "1h"   # daily-style decisions are taken on the 1h close in this data set


def load_cached(asset: str, tf: str) -> pd.DataFrame | None:
    path = DATA_DIR / f"{asset}__{tf}.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path)
    df["ts"] = pd.to_datetime(df["ts"], utc=True, errors="coerce")
    df = df.dropna(subset=["ts"]).sort_values("ts").reset_index(drop=True)
    for col in ("open", "high", "low", "close", "volume"):
        if col not in df:
            df[col] = np.nan
    return df[["ts", "open", "high", "low", "close", "volume"]]


def class_of(asset: str) -> str:
    """True asset class of a pair, independent of which universe loop reached it."""
    for cls in ("crypto", "fx", "equity"):
        if asset in UNIVERSE[cls][0]:
            return cls
    return "other"


# --------------------------------------------------------------------------- simulations
def bracket_trades(df: pd.DataFrame, sig: np.ndarray, exit_cfg: dict, cost_atr: float,
                   lo: int = 0, hi: int | None = None) -> pd.DataFrame:
    """Bracketed simulation restricted to the entry-index window [lo, hi)."""
    ind = core.indicators(df)
    atr = ind["atr"].to_numpy()
    n = len(df)
    hi = n if hi is None else min(hi, n)
    entries = [(i, int(sig[i])) for i in range(max(lo, 1), hi - 1) if int(sig[i]) != 0]
    if not entries:
        return pd.DataFrame()
    return v1bt.simulate_entries(df, entries, atr, exit_cfg["tp_atr"], exit_cfg["sl_atr"],
                                 exit_cfg["max_bars"], cost_atr, engine="bracket")


def expiry_trades(df: pd.DataFrame, sig: np.ndarray, horizon: int,
                  lo: int = 0, hi: int | None = None) -> pd.DataFrame:
    """Fixed-expiry direction bet: enter next open, settle on the close `horizon` bars later."""
    o = df["open"].to_numpy(float)
    c = df["close"].to_numpy(float)
    ts = df["ts"].to_numpy()
    n = len(df)
    hi = n if hi is None else min(hi, n)
    rows = []
    free_from = 0
    for i in range(max(lo, 1), hi - 1):
        side = int(sig[i])
        if side == 0 or i < free_from:
            continue
        entry_i = i + 1
        exit_i = entry_i + horizon - 1
        if exit_i >= n:
            break
        entry, exit_price = o[entry_i], c[exit_i]
        move = side * (exit_price - entry) / entry if entry else np.nan
        rows.append({"engine": "expiry", "entry_ts": ts[entry_i], "exit_ts": ts[exit_i], "side": side,
                     "entry": entry, "exit": exit_price, "bars": horizon,
                     "atr": np.nan, "pnl_atr": np.nan, "ret": move,
                     "outcome": "win" if move > 0 else ("loss" if move < 0 else "flat")})
        free_from = exit_i + 1
    return pd.DataFrame(rows)


def placebo_entries(sig: np.ndarray, long_count: int, short_count: int, lo: int, hi: int,
                    seed: int) -> np.ndarray:
    """Random entries inside [lo, hi) with exactly the signal's long and short counts.

    Matching both counts (not just the share) keeps the placebo's exposure to market drift
    identical to the strategy's, so any difference in outcome is timing, not direction.
    """
    n = len(sig)
    hi = min(hi, n - 2)
    out = np.zeros(n, dtype=np.int8)
    room = hi - lo
    total = long_count + short_count
    if room <= 0 or total <= 0:
        return out
    take = min(total, room)
    rng = np.random.default_rng(seed)
    idx = rng.choice(np.arange(lo, hi), size=take, replace=False)
    sides = np.r_[np.ones(long_count, np.int8), -np.ones(short_count, np.int8)][:take]
    rng.shuffle(sides)
    out[idx] = sides
    return out


# --------------------------------------------------------------------------- metrics
def bracket_metrics(trades: pd.DataFrame, tp: float, sl: float) -> dict:
    return v1bt.metrics(trades, tp, sl)


def expiry_metrics(trades: pd.DataFrame, payout: float) -> dict:
    if trades.empty:
        return {"n": 0}
    win = trades["outcome"].to_numpy() == "win"
    n = len(trades)
    wr = float(win.mean())
    be = 1.0 / (1.0 + payout)
    pnl = np.where(win, payout, -1.0)          # per unit staked
    equity = np.cumsum(pnl)
    peak = np.maximum.accumulate(np.r_[0.0, equity])[1:]
    z = (win.sum() - n * be) / math.sqrt(n * be * (1 - be)) if n else float("nan")
    return {"n": n, "wins": int(win.sum()), "wr": wr, "parity": be, "excess_pp": (wr - be) * 100,
            "z_vs_parity": float(z), "expectancy_atr": float(pnl.mean()), "total_atr": float(pnl.sum()),
            "pf": float(pnl[pnl > 0].sum() / -pnl[pnl < 0].sum()) if (pnl < 0).any() else float("inf"),
            "max_dd_atr": float(np.max(peak - equity)), "avg_bars": float(trades["bars"].mean()),
            "time_share": 0.0, "pnl_wr": wr}


def iter_pairs(strategy: Strategy):
    """Yield (asset_class, asset, tf, frame) once per pair, skipping classes that repeat it."""
    seen: set = set()
    for asset_class in strategy.asset_classes:
        universe, avail = UNIVERSE[asset_class]
        for asset in universe:
            for tf in strategy.timeframes:
                if tf not in avail or (asset, tf) in seen:
                    continue
                seen.add((asset, tf))
                df = load_cached(asset, tf)
                if df is None or len(df) < 400:
                    continue
                yield asset_class, asset, tf, df


def _pool(frames: list[pd.DataFrame]) -> pd.DataFrame:
    frames = [f for f in frames if not f.empty]
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


# --------------------------------------------------------------------------- driver
def evaluate(strategy: Strategy, split: float = 0.6, cost_atr: float = 0.02,
             payout: float = 0.80, seed: int = 11) -> dict:
    """Run one strategy across its whole universe and return per-pair rows plus pooled controls."""
    if strategy.signal_fn is None:
        return {"id": strategy.id, "name": strategy.name, "mode": strategy.mode,
                "status": "signal-only", "rows": [], "pooled": {}, "placebo": {},
                "notes": strategy.notes}

    rows, test_frames, train_frames, plc_frames = [], [], [], []

    for asset_class, asset, tf, df in iter_pairs(strategy):
        ind, sig = strategy.signal_fn(df, dict(strategy.params))
        nsig = int(np.count_nonzero(sig))
        if nsig == 0:
            rows.append({"asset": asset, "tf": tf, "class": class_of(asset), "n_test": 0,
                         "note": "no signals"})
            continue
        cut = int(len(df) * split)
        seg = sig[cut:]
        long_n = int((seg > 0).sum())
        short_n = int((seg < 0).sum())
        if len(seg) < 60 or long_n + short_n < 3:
            rows.append({"asset": asset, "tf": tf, "class": class_of(asset),
                         "n_test": 0, "note": "too few test signals"})
            continue
        if strategy.mode == "expiry":
            h = int(strategy.exit.get("expiry_bars", 3))
            tr_tr = expiry_trades(df, sig, h, 0, cut)
            tr_te = expiry_trades(df, sig, h, cut, len(df))
            m_tr, m_te = expiry_metrics(tr_tr, payout), expiry_metrics(tr_te, payout)
            sim = lambda s, d=df, hz=h: expiry_trades(d, s, hz, cut, len(d))
            met = lambda t: expiry_metrics(t, payout)
            hi_pl = len(df) - h - 1
        else:
            tp, sl = strategy.exit["tp_atr"], strategy.exit["sl_atr"]
            tr_tr = bracket_trades(df, sig, strategy.exit, cost_atr, 0, cut)
            tr_te = bracket_trades(df, sig, strategy.exit, cost_atr, cut, len(df))
            m_tr, m_te = bracket_metrics(tr_tr, tp, sl), bracket_metrics(tr_te, tp, sl)
            sim, met = lambda s, d=df: bracket_trades(d, s, strategy.exit, cost_atr, cut, len(d)), \
                lambda t: bracket_metrics(t, tp, sl)
            hi_pl = len(df) - 2
        reps = [_placebo_rep(sim, met, sig, long_n, short_n, cut + 60, hi_pl, seed + r)
                for r in range(N_PLACEBO)]
        m_pl = {k: float(np.nanmean([r.get(k, np.nan) for r in reps])) for k in ("excess_pp", "expectancy_atr")}
        m_pl["n"] = float(np.nanmean([r.get("n", 0) for r in reps]))
        p_val = float(np.mean([r.get("excess_pp", -99) >= m_te["excess_pp"] for r in reps]))
        if not m_te.get("n"):
            rows.append({"asset": asset, "tf": tf, "class": class_of(asset), "n_test": 0,
                         "n_sig_test": int(np.count_nonzero(sig[cut:]))})
            continue
        rows.append({
            "asset": asset, "tf": tf, "class": class_of(asset), "asset_class": asset_class,
            "n_test": m_te["n"], "wr_test": m_te["wr"], "parity": m_te["parity"],
            "excess_pp": m_te["excess_pp"], "z": m_te["z_vs_parity"],
            "exp_atr": m_te["expectancy_atr"], "pf": m_te["pf"],
            "time_share": m_te["time_share"], "pnl_wr": m_te["pnl_wr"],
            "n_train": m_tr.get("n", 0), "wr_train": m_tr.get("wr", float("nan")),
            "exp_train": m_tr.get("expectancy_atr", float("nan")),
            "placebo_exp": m_pl.get("expectancy_atr", float("nan")),
            "placebo_excess_pp": m_pl.get("excess_pp", float("nan")),
            "lift_pp": m_te["excess_pp"] - m_pl.get("excess_pp", float("nan")),
            "p_value": p_val,
        })
        test_frames.append(tr_te)
        train_frames.append(tr_tr)

    pooled = _pooled_score(strategy, _pool(test_frames), payout, test=True)
    pooled_train = _pooled_score(strategy, _pool(train_frames), payout, test=False)
    scored = [r for r in rows if r.get("n_test")]
    plc = {"n": float(np.sum([r.get("n_test", 0) for r in scored])),
           "excess_pp": float(np.nanmean([r.get("placebo_excess_pp", np.nan) for r in scored])) if scored else float("nan"),
           "expectancy_atr": float(np.nanmean([r.get("placebo_exp", np.nan) for r in scored])) if scored else float("nan")}
    p_overall = float(np.nanmedian([r.get("p_value", np.nan) for r in scored])) if scored else float("nan")
    return {"id": strategy.id, "name": strategy.name, "mode": strategy.mode, "status": "scored",
            "exit": strategy.exit, "rows": rows, "pooled": pooled, "pooled_train": pooled_train,
            "placebo": plc, "notes": strategy.notes, "p_value": p_overall,
            "lift_pp": (pooled.get("excess_pp", float("nan")) - plc.get("excess_pp", float("nan")))}


N_PLACEBO = 12


def _placebo_rep(sim, met, sig: np.ndarray, long_n: int, short_n: int, lo: int, hi: int, seed: int) -> dict:
    ps = placebo_entries(sig, long_n, short_n, lo, hi, seed)
    m = met(sim(ps))
    return m if m.get("n") else {"excess_pp": float("nan"), "expectancy_atr": float("nan"), "n": 0}


def _pooled_score(strategy: Strategy, trades: pd.DataFrame, payout: float, test: bool) -> dict:
    if trades.empty:
        return {"n": 0}
    if strategy.mode == "expiry":
        m = expiry_metrics(trades, payout)
    else:
        m = bracket_metrics(trades, strategy.exit["tp_atr"], strategy.exit["sl_atr"])
    m["slice"] = "test" if test else "train"
    return m


def verdict(result: dict) -> str:
    """One-word call used in the summary tables.

    Deliberately strict: positive expectancy alone is not an edge. The strategy must also beat
    the drift-matched placebo with p <= 0.10 (no more than 1 in 10 random-entry replications
    doing as well) before it is called confirmed.
    """
    if result.get("status") != "scored":
        return "unvalidated"
    p, pl = result["pooled"], result["placebo"]
    if not p.get("n") or p["n"] < 30:
        return "insufficient sample"
    if p["expectancy_atr"] <= 0:
        return "no edge after costs"
    if p["excess_pp"] <= 0:
        return "fails parity"
    if pl.get("n") and p["excess_pp"] - pl.get("excess_pp", 0) <= 0:
        return "fails placebo"
    pv = result.get("p_value", float("nan"))
    if pv == pv and pv <= 0.10:
        return "edge confirmed"
    return "promising, not significant"
