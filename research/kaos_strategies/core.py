"""Shared scaffolding for the KAOS strategy library.

One registry, one indicator set, one execution convention. Strategies differ only in the
signal they emit and the exit structure they declare, so every strategy is scored by the
same engine - which is the only way a comparison table means anything.

Asset classes: crypto, fx, equity, binary, options.
Execution modes:
    bracket  - target/stop in ATR multiples, optional bar expiry (futures, FX, equities, spot)
    expiry   - fixed bar expiry, direction only (binary options)
    manual   - signal only, structure chosen by the trader (options)
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import time
from pathlib import Path
from typing import Callable
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
V1 = HERE.parent / "kaos_strategy"
sys.path.insert(0, str(V1))

import strategy as v1  # noqa: E402  (indicators shared with KAOS Strategy v1)

ASSET_CLASSES = ("crypto", "fx", "equity", "binary", "options")


# --------------------------------------------------------------------------- registry
@dataclass
class Strategy:
    id: str
    name: str
    asset_classes: tuple[str, ...]
    timeframes: tuple[str, ...]
    thesis: str
    mode: str                      # bracket | expiry | manual
    params: dict
    signal_fn: Callable | None = None
    exit: dict = field(default_factory=dict)
    platforms: tuple[str, ...] = ()
    validated: bool = True
    notes: str = ""


REGISTRY: dict[str, Strategy] = {}


def register(strategy: Strategy) -> Strategy:
    if strategy.id in REGISTRY:
        raise ValueError(f"duplicate strategy id {strategy.id}")
    REGISTRY[strategy.id] = strategy
    return strategy


def get(strategy_id: str) -> Strategy:
    return REGISTRY[strategy_id]


def by_asset_class(asset_class: str) -> list[Strategy]:
    return [s for s in REGISTRY.values() if asset_class in s.asset_classes]


# ------------------------------------------------------------------------- indicators
def indicators(df: pd.DataFrame, p: v1.Params = v1.DEFAULT) -> pd.DataFrame:
    """v1 indicators plus the extras this library needs."""
    ind = v1.indicators(df, p)
    high, low, close = ind["high"], ind["low"], ind["close"]
    ind["atr_pct"] = ind["atr"] / close.replace(0, np.nan)
    ind["atr_ma"] = ind["atr"].rolling(50, min_periods=20).mean()
    ind["atr_expansion"] = ind["atr"] / ind["atr_ma"].replace(0, np.nan)
    ind["hh20"] = high.rolling(20).max().shift(1)
    ind["ll20"] = low.rolling(20).min().shift(1)
    ind["vol_ma"] = ind["volume"].rolling(20, min_periods=5).mean()
    ind["body"] = (close - ind["open"]).abs()
    ind["range"] = (high - low).replace(0, np.nan)
    ind["close_pos"] = (close - low) / ind["range"]
    return ind


# --------------------------------------------------------------------------- sessions
@dataclass(frozen=True)
class Session:
    tz: str
    start: time
    end: time


US_EQUITY = Session("America/New_York", time(9, 30), time(16, 0))
LONDON = Session("Europe/London", time(8, 0), time(16, 30))
NEW_YORK_FX = Session("America/New_York", time(8, 0), time(17, 0))


def add_session(df: pd.DataFrame, session: Session) -> pd.DataFrame:
    """Mark bars inside a cash session and index them from the session open."""
    out = df.copy()
    local = out["ts"].dt.tz_convert(ZoneInfo(session.tz))
    clock = local.dt.time
    out["in_session"] = (clock >= session.start) & (clock < session.end)
    out["session_date"] = local.dt.date
    # count only bars that are actually inside the session, so bar 0 is the session open
    # even when the feed carries the other 20 hours of the day (FX) or pre/post market.
    out["bar_in_session"] = -1
    seq = out.loc[out["in_session"]].groupby("session_date").cumcount()
    out.loc[seq.index, "bar_in_session"] = seq.to_numpy()
    return out


def opening_range(df: pd.DataFrame, session: Session, bars: int) -> pd.DataFrame:
    """High/low of the first `bars` in-session bars, broadcast to the whole session."""
    out = add_session(df, session)
    in_sess = out[out["in_session"]]
    agg = (in_sess[in_sess["bar_in_session"] < bars]
           .groupby("session_date")
           .agg(or_high=("high", "max"), or_low=("low", "min"), or_bars=("high", "size")))
    out = out.merge(agg, left_on="session_date", right_index=True, how="left")
    out["or_high"] = out["or_high"].where(out["or_bars"].fillna(0) >= bars)
    out["or_low"] = out["or_low"].where(out["or_bars"].fillna(0) >= bars)
    return out


# ------------------------------------------------------------------------- signal util
def to_signal(long_mask: np.ndarray, short_mask: np.ndarray, usable: np.ndarray) -> np.ndarray:
    sig = np.where(usable & long_mask, 1, np.where(usable & short_mask, -1, 0))
    return sig.astype(np.int8)


def usable_atr(ind: pd.DataFrame) -> np.ndarray:
    atr = ind["atr"].to_numpy()
    return np.isfinite(atr) & (atr > 0)
