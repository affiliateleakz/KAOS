"""The strategies themselves.

Each `signal_fn(df, params)` returns `(ind, sig)` where `sig` is +1/-1/0 per bar, decided on
that bar's close. The declared `exit` block tells the engine how to trade it.

Nothing here is tuned on the test data. The two v1 engines keep the brackets that were fixed
in the KAOS Strategy v1 study (3.0/5.0 ATR and 1.6/1.0 ATR), and the three breakout/expansion
strategies use the textbook 1 ATR stop / 2 ATR target that you would write down before looking
at a chart.
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np
import pandas as pd

import core
from core import LONDON, NEW_YORK_FX, US_EQUITY, Strategy, indicators, opening_range, register, to_signal, usable_atr
import strategy as v1


def _params(base: dict, overrides: dict) -> v1.Params:
    """v1 Params with only the keys this library actually overrides."""
    allowed = {k: v for k, v in overrides.items() if k in v1.Params.__dataclass_fields__}
    return replace(v1.DEFAULT, **{**base, **allowed})


def _first_per_session(sig: np.ndarray, session_date) -> np.ndarray:
    """Keep only the first signal of each (session, direction) pair."""
    seen: set = set()
    out = np.zeros_like(sig)
    for i in np.flatnonzero(sig != 0):
        key = (session_date[i], int(np.sign(sig[i])))
        if key in seen:
            continue
        seen.add(key)
        out[i] = sig[i]
    return out


# ------------------------------------------------------------------ 1. PULSE (range MR)
def _pulse(df: pd.DataFrame, p: dict):
    params = _params({"mode": "pulse"}, p)
    ind = indicators(df, params)
    return ind, v1.signal_series(ind, params)


register(Strategy(
    id="pulse-range",
    name="KAOS Pulse - range mean reversion",
    asset_classes=("crypto", "fx", "equity", "binary"),
    timeframes=("1m", "5m", "15m", "1h", "4h"),
    thesis=("Inside a non-trending regime (efficiency ratio <= 0.28) a price stretched at least 1 ATR "
            "from EMA20, with RSI stretched and outside the Bollinger band, tends to revert. "
            "A 3 ATR target against a 5 ATR stop converts that tendency into a high hit rate."),
    mode="bracket",
    params={"z_entry": 1.0, "rsi_pulse": 42.0, "er_range_max": 0.28},
    signal_fn=_pulse,
    exit={"kind": "bracket", "tp_atr": 3.0, "sl_atr": 5.0, "max_bars": 24},
    platforms=("pocketoption", "kraken", "coinbase", "binance", "mt5", "oanda", "tastytrade", "alpaca"),
))


# ------------------------------------------------------------------ 2. DRIVE (trend pullback)
def _drive(df: pd.DataFrame, p: dict):
    params = _params({"mode": "drive"}, p)
    ind = indicators(df, params)
    return ind, v1.signal_series(ind, params)


register(Strategy(
    id="drive-trend",
    name="KAOS Drive - trend pullback",
    asset_classes=("crypto", "fx", "equity"),
    timeframes=("15m", "1h", "4h"),
    thesis=("When the efficiency ratio is above 0.30, EMA20 sits on the correct side of EMA50 and a bar "
            "dips into EMA20 before closing back with the trend, the trend is more likely to continue."),
    mode="bracket",
    params={"er_trend_min": 0.30},
    signal_fn=_drive,
    exit={"kind": "bracket", "tp_atr": 1.6, "sl_atr": 1.0, "max_bars": 24},
    platforms=("kraken", "coinbase", "binance", "mt5", "oanda", "tastytrade", "alpaca"),
    notes="Ships disabled: the v1 study found no expectancy edge out of sample. Kept for completeness.",
))


# ------------------------------------------------------------------ 3. ORB (US equities)
def _orb(df: pd.DataFrame, p: dict):
    bars = int(p.get("or_bars", 3))
    ind = indicators(opening_range(df, US_EQUITY, bars))
    close = ind["close"].to_numpy()
    or_high = ind["or_high"].to_numpy()
    or_low = ind["or_low"].to_numpy()
    pos = ind["close_pos"].to_numpy()
    in_sess = ind["in_session"].to_numpy()
    bar_n = ind["bar_in_session"].to_numpy()
    # give the range time to form, then allow ~35 bars of breakout attempts
    window = (bar_n >= bars) & (bar_n <= bars + 35)
    long_m = in_sess & window & (close > or_high) & (pos > 0.6)
    short_m = in_sess & window & (close < or_low) & (pos < 0.4)
    usable = usable_atr(ind) & np.isfinite(or_high)
    sig = to_signal(long_m, short_m, usable)
    return ind, _first_per_session(sig, ind["session_date"].to_numpy())


register(Strategy(
    id="orb-equity",
    name="KAOS ORB - US opening range breakout",
    asset_classes=("equity",),
    timeframes=("5m", "15m"),
    thesis=("The first 30-45 minutes of the US cash session set a reference range. A close outside that "
            "range, in the direction of the closing candle, is taken once per session because the first "
            "decisive break carries the day's order flow."),
    mode="bracket",
    params={"or_bars": 3},
    signal_fn=_orb,
    exit={"kind": "bracket", "tp_atr": 2.0, "sl_atr": 1.0, "max_bars": 24},
    platforms=("tastytrade", "alpaca", "mt5"),
))


# ------------------------------------------------------------------ 4. FX session breakout
def _fx_session(df: pd.DataFrame, p: dict):
    session = LONDON if p.get("session", "london") == "london" else NEW_YORK_FX
    bars = int(p.get("or_bars", 4))
    ind = indicators(opening_range(df, session, bars))
    close = ind["close"].to_numpy()
    or_high = ind["or_high"].to_numpy()
    or_low = ind["or_low"].to_numpy()
    pos = ind["close_pos"].to_numpy()
    in_sess = ind["in_session"].to_numpy()
    bar_n = ind["bar_in_session"].to_numpy()
    window = (bar_n >= bars) & (bar_n <= bars + 40)
    long_m = in_sess & window & (close > or_high) & (pos > 0.55)
    short_m = in_sess & window & (close < or_low) & (pos < 0.45)
    usable = usable_atr(ind) & np.isfinite(or_high)
    sig = to_signal(long_m, short_m, usable)
    return ind, _first_per_session(sig, ind["session_date"].to_numpy())


register(Strategy(
    id="fx-session-breakout",
    name="KAOS FX Session - London open range breakout",
    asset_classes=("fx",),
    timeframes=("5m", "15m"),
    thesis=("The London open concentrates the day's order flow into a narrow range. The first decisive "
            "close outside that opening range tends to extend through the session."),
    mode="bracket",
    params={"or_bars": 4, "session": "london"},
    signal_fn=_fx_session,
    exit={"kind": "bracket", "tp_atr": 2.0, "sl_atr": 1.0, "max_bars": 24},
    platforms=("mt5", "oanda", "kraken"),
))


# ------------------------------------------------------------------ 5. Crypto ignition
def _ignition(df: pd.DataFrame, p: dict):
    ind = indicators(df)
    close = ind["close"].to_numpy()
    open_ = ind["open"].to_numpy()
    hh = ind["hh20"].to_numpy()
    ll = ind["ll20"].to_numpy()
    expansion = ind["atr_expansion"].to_numpy()
    body = ind["body"].to_numpy()
    thrust = body / ind["range"].to_numpy()
    er = np.nan_to_num(ind["er"].to_numpy())
    need = p.get("expansion", 1.15)
    long_m = (close > hh) & (expansion >= need) & (thrust > 0.5) & (close > open_)
    short_m = (close < ll) & (expansion >= need) & (thrust > 0.5) & (close < open_)
    sig = to_signal(long_m, short_m, usable_atr(ind) & (er >= p.get("er_min", 0.20)))
    return ind, sig


register(Strategy(
    id="crypto-ignition",
    name="KAOS Ignition - volatility expansion breakout",
    asset_classes=("crypto",),
    timeframes=("5m", "15m", "1h", "4h"),
    thesis=("Crypto pays for volatility expansion, not for value. A close through the 20-bar extreme on a "
            "bar with above-average range and a dominant body marks the start of a directional push."),
    mode="bracket",
    params={"expansion": 1.15, "er_min": 0.20},
    signal_fn=_ignition,
    exit={"kind": "bracket", "tp_atr": 3.0, "sl_atr": 1.5, "max_bars": 24},
    platforms=("kraken", "coinbase", "binance", "pocketoption"),
))


# ------------------------------------------------------------------ 6. Binary fixed expiry
def _binary_fade(df: pd.DataFrame, p: dict):
    params = _params({"mode": "pulse"}, {})
    ind = indicators(df, params)
    reg = v1.regime(ind, params)
    z = ind["z"].to_numpy()
    rsi = ind["rsi"].to_numpy()
    zx = p.get("z", 1.0)
    rx = p.get("rsi", 40.0)
    long_m = (reg == 0) & (z <= -zx) & (rsi <= rx)
    short_m = (reg == 0) & (z >= zx) & (rsi >= 100 - rx)
    sig = to_signal(long_m, short_m, usable_atr(ind))
    return ind, sig


register(Strategy(
    id="binary-fade",
    name="KAOS Binary - range fade, fixed expiry",
    asset_classes=("binary",),
    timeframes=("1m", "5m"),
    thesis=("Binary options have no stop, so only the close at expiry matters. In a range regime a "
            "stretched price has a better-than-even chance of closing back toward the mean within 3 bars."),
    mode="expiry",
    params={"z": 1.0, "rsi": 40.0, "expiry_bars": 3},
    signal_fn=_binary_fade,
    exit={"kind": "expiry", "expiry_bars": 3},
    platforms=("pocketoption",),
))


# ------------------------------------------------------------------ 7. Options structure
register(Strategy(
    id="options-credit",
    name="KAOS Options - defined-risk premium selling",
    asset_classes=("options",),
    timeframes=("1d",),
    thesis=("Sell defined-risk premium only when the underlying is range-bound and realised volatility sits "
            "below its own median; buy debit spreads when a trend regime and rising volatility coincide. "
            "The signal chooses the structure, not just the direction."),
    mode="manual",
    params={"dte": 35, "short_delta": 0.18, "width": 5, "profit_target": 0.5, "stop": 2.0},
    signal_fn=None,
    exit={"kind": "manual"},
    platforms=("tastytrade",),
    validated=False,
    notes=("Signal-only. Options chains are not in the public data set, so no P&L is claimed here. "
           "The rules are complete and executable; validation needs an OPRA/ORATS chain feed."),
))
