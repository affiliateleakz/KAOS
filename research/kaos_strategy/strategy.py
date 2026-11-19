"""KAOS Strategy - a timeframe- and asset-agnostic rule set.

Design constraints that make it portable:

* Every parameter is expressed in *bars* or in *ATR units*, never in pips, dollars,
  percent or clock time. The same parameters therefore apply to a 5s crypto candle,
  a 5m FX candle and a 4h equity candle without re-tuning.
* The module never places orders. It emits a normalised intent that any platform can
  translate: side, entry reference, stop, target, ATR, and a bar-counted expiry.
* Two engines share the same brackets: PULSE (mean reversion inside a range regime)
  and DRIVE (continuation inside a trend regime). Regime selection is what keeps the
  win rate high: PULSE only fires when the market is not trending.

The regime filter is a Kaufman efficiency ratio. ER distinguishes a market that is
moving in one direction (ER -> 1) from one that is chopping (ER -> 0). PULSE trades the
chop, DRIVE trades the direction, and neither trades the ambiguous middle.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict, field

import numpy as np
import pandas as pd


# --------------------------------------------------------------------------- params
@dataclass
class Params:
    # regime
    er_len: int = 20
    er_range_max: float = 0.28      # below this the market is chopping -> PULSE
    er_trend_min: float = 0.30      # above this the market is directional -> DRIVE
    # trend context
    ema_fast: int = 20
    ema_slow: int = 50
    atr_len: int = 14
    rsi_len: int = 14
    bb_len: int = 20
    bb_sd: float = 2.0
    # entries
    z_entry: float = 1.0            # ATR-normalised distance from EMA20 for PULSE
    rsi_pulse: float = 42.0         # RSI must also be stretched this far
    knive_guard: float = 2.0        # skip PULSE when price is this many ATR from EMA50
    # brackets (ATR multiples). 3.0/5.0 with a 24-bar expiry is the profile that was
    # validated out of sample in RESULTS.md; the earlier 0.8/1.2 produced 46-59% win rates.
    tp_atr: float = 3.0
    sl_atr: float = 5.0
    max_bars: int = 24
    # DRIVE brackets
    dr_tp_atr: float = 1.6
    dr_sl_atr: float = 1.0
    dr_max_bars: int = 24
    mode: str = "pulse"             # pulse | drive | both (DRIVE has no measured edge)

    def as_dict(self) -> dict:
        return asdict(self)


DEFAULT = Params()


# ------------------------------------------------------------------------ indicators
def indicators(df: pd.DataFrame, p: Params = DEFAULT) -> pd.DataFrame:
    """Return a frame with every derived column the signal engine needs."""
    out = df.copy()
    high, low, close = out["high"], out["low"], out["close"]

    prev_close = close.shift(1)
    tr = pd.concat([(high - low).abs(), (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    out["atr"] = tr.ewm(alpha=1 / p.atr_len, adjust=False, min_periods=p.atr_len).mean()
    out["ema_fast"] = close.ewm(span=p.ema_fast, adjust=False).mean()
    out["ema_slow"] = close.ewm(span=p.ema_slow, adjust=False).mean()

    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / p.rsi_len, adjust=False, min_periods=p.rsi_len).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / p.rsi_len, adjust=False, min_periods=p.rsi_len).mean()
    out["rsi"] = 100 - 100 / (1 + gain / loss.replace(0, np.nan))

    mid = close.rolling(p.bb_len).mean()
    sd = close.rolling(p.bb_len).std(ddof=0)
    out["bb_mid"] = mid
    out["bb_up"] = mid + p.bb_sd * sd
    out["bb_lo"] = mid - p.bb_sd * sd

    # Kaufman efficiency ratio: net move divided by the path actually travelled.
    net = (close - close.shift(p.er_len)).abs()
    path = close.diff().abs().rolling(p.er_len).sum()
    out["er"] = (net / path.replace(0, np.nan)).clip(0, 1)

    out["z"] = (close - out["ema_fast"]) / out["atr"].replace(0, np.nan)
    out["z_slow"] = (close - out["ema_slow"]) / out["atr"].replace(0, np.nan)
    out["er_slope"] = out["er"].diff()
    return out


def regime(ind: pd.DataFrame, p: Params = DEFAULT) -> np.ndarray:
    """+1 trend up, -1 trend down, 0 range, -9 undecided (no trade)."""
    er = ind["er"].to_numpy()
    higher = (ind["ema_fast"] > ind["ema_slow"]).to_numpy()
    lower = (ind["ema_fast"] < ind["ema_slow"]).to_numpy()
    strong = (ind["z_slow"].abs() > 0.5).to_numpy()

    out = np.full(len(ind), -9, dtype=np.int8)
    trend = (er >= p.er_trend_min) & strong
    out[trend & higher] = 1
    out[trend & lower] = -1
    chop = er <= p.er_range_max
    out[chop] = 0
    return out


# --------------------------------------------------------------------------- signals
def signal_series(ind: pd.DataFrame, p: Params = DEFAULT) -> np.ndarray:
    """Return +1 (long), -1 (short), 0 (flat) evaluated at each bar's close."""
    reg = regime(ind, p)
    close = ind["close"].to_numpy()
    open_ = ind["open"].to_numpy()
    z = ind["z"].to_numpy()
    z_slow = ind["z_slow"].to_numpy()
    rsi = ind["rsi"].to_numpy()
    bb_lo = ind["bb_lo"].to_numpy()
    bb_up = ind["bb_up"].to_numpy()
    ema_f = ind["ema_fast"].to_numpy()
    er_slope = ind["er_slope"].to_numpy()
    atr = ind["atr"].to_numpy()

    sig = np.zeros(len(ind), dtype=np.int8)
    usable = np.isfinite(atr) & (atr > 0)

    if p.mode in ("pulse", "both"):
        long_p = (reg == 0) & (z <= -p.z_entry) & (rsi <= p.rsi_pulse) & (close < bb_lo) & (z_slow > -p.knive_guard)
        short_p = (reg == 0) & (z >= p.z_entry) & (rsi >= 100 - p.rsi_pulse) & (close > bb_up) & (z_slow < p.knive_guard)
        sig[long_p & usable] = 1
        sig[short_p & usable] = -1

    if p.mode in ("drive", "both"):
        pull_long = (reg == 1) & (ind["low"].to_numpy() <= ema_f) & (close > ema_f) & (close > open_) & (er_slope > 0)
        pull_short = (reg == -1) & (ind["high"].to_numpy() >= ema_f) & (close < ema_f) & (close < open_) & (er_slope > 0)
        sig[pull_long & usable] = 1
        sig[pull_short & usable] = -1

    return sig


def brackets(side: int, price: float, atr: float, p: Params = DEFAULT, engine: str = "pulse") -> tuple[float, float]:
    tp, sl = (p.tp_atr, p.sl_atr) if engine == "pulse" else (p.dr_tp_atr, p.dr_sl_atr)
    if side > 0:
        return price + tp * atr, price - sl * atr
    return price - tp * atr, price + sl * atr


def engine_of(ind_row, p: Params = DEFAULT) -> str:
    return "pulse" if ind_row["reg"] == 0 else "drive"


# -------------------------------------------------------------------- live interface
def evaluate(df: pd.DataFrame, p: Params = DEFAULT, bar_seconds: float | None = None) -> dict:
    """Evaluate the most recent closed bar and return a platform-neutral intent."""
    ind = indicators(df, p)
    ind["reg"] = regime(ind, p)
    sig = signal_series(ind, p)
    last = ind.iloc[-1]
    side = int(sig[-1])
    reg = int(last["reg"])
    engine = "pulse" if reg == 0 else ("drive" if reg in (1, -1) else "none")
    atr = float(last["atr"]) if np.isfinite(last["atr"]) else 0.0

    intent = {
        "ts": str(last["ts"]),
        "side": "long" if side > 0 else ("short" if side < 0 else "flat"),
        "regime": {1: "trend_up", -1: "trend_down", 0: "range", -9: "undecided"}[reg],
        "engine": engine,
        "price": float(last["close"]),
        "atr": atr,
        "er": float(last["er"]) if np.isfinite(last["er"]) else None,
        "rsi": float(last["rsi"]) if np.isfinite(last["rsi"]) else None,
        "z": float(last["z"]) if np.isfinite(last["z"]) else None,
        "tradeable": side != 0 and atr > 0,
    }
    if intent["tradeable"]:
        tp, sl = brackets(side, intent["price"], atr, p, engine)
        bars = p.max_bars if engine == "pulse" else p.dr_max_bars
        intent.update({
            "stop": sl,
            "target": tp,
            "reward_risk": round(abs(tp - intent["price"]) / abs(intent["price"] - sl), 3),
            "expiry_bars": bars,
            "expiry_seconds": int(bars * bar_seconds) if bar_seconds else None,
        })
    return intent


def binary_option_intent(df: pd.DataFrame, p: Params = DEFAULT, expiry_seconds: int = 300) -> dict:
    """Pocket Option / binary style: direction only, fixed expiry, no stops."""
    intent = evaluate(df, p)
    if not intent["tradeable"]:
        return {**intent, "contract": None}
    return {**intent,
            "contract": "call" if intent["side"] == "long" else "put",
            "expiry_seconds": expiry_seconds,
            "note": "Binary payout needs a hit rate above 1/(1+payout); 0.80 payout breaks even at 55.6%."}


def mt5_intent(df: pd.DataFrame, p: Params = DEFAULT, lot: float = 0.01) -> dict:
    """MetaTrader style bracket order."""
    intent = evaluate(df, p)
    if not intent["tradeable"]:
        return {**intent, "order": None}
    return {**intent,
            "order": {"type": "buy_limit" if intent["side"] == "long" else "sell_limit",
                      "volume": lot, "price": intent["price"],
                      "sl": intent["stop"], "tp": intent["target"]}}


if __name__ == "__main__":
    import data

    frame = data.load("BTCUSD", "5m")
    print(frame.tail(3).to_string(index=False))
    print(evaluate(frame, DEFAULT, bar_seconds=300))
