"""KAOS Structure v2 signal rules, vendored unchanged from research/strategy_v2_1/kaos_strategy.py.

UNVALIDATED: the v2.1 archival audit was a FAIL (net negative after costs). Used here only to
drive paper trades with a documented reason; it is not evidence of profitability.
"""
import numpy as np
import pandas as pd

STRATEGY_NAME = "KAOS Structure v2"
STRATEGY_STATUS = "Unvalidated research strategy (v2.1 archival audit: FAIL). Paper only."
WARMUP_BARS = 56


def features(raw):
    d = raw.copy().reset_index(drop=True)
    d.columns = [str(c).lower() for c in d.columns]
    required = ['open', 'high', 'low', 'close']
    if not all(c in d for c in required):
        raise ValueError('Required: open high low close')
    for c in required:
        d[c] = pd.to_numeric(d[c], errors='raise')
    if (d[required].isna().any().any() or (d[required] <= 0).any().any() or
            (d.high < d[['open', 'close', 'low']].max(axis=1)).any() or
            (d.low > d[['open', 'close', 'high']].min(axis=1)).any()):
        raise ValueError('Invalid OHLC')
    d['ema20'] = d.close.ewm(span=20, adjust=False).mean()
    d['ema50'] = d.close.ewm(span=50, adjust=False).mean()
    tr = pd.concat([(d.high - d.low), (d.high - d.close.shift()).abs(), (d.low - d.close.shift()).abs()], axis=1).max(axis=1)
    d['atr'] = tr.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    d['prior_high'] = d.high.shift(1).rolling(20).max()
    d['prior_low'] = d.low.shift(1).rolling(20).min()
    d['vol_base'] = d.volume.shift(1).rolling(20).median() if 'volume' in d else np.nan
    return d


def generate(raw):
    """Signals only on closed bars. Two structural setups, same rules for all asset types."""
    d = features(raw)
    up = (d.ema20 > d.ema50) & (d.ema20 > d.ema20.shift(4))
    down = (d.ema20 < d.ema50) & (d.ema20 < d.ema20.shift(4))
    bullish = (d.close > d.open) & ((d.close - d.open) >= 0.45 * (d.high - d.low))
    bearish = (d.close < d.open) & ((d.open - d.close) >= 0.45 * (d.high - d.low))
    volok = (d.volume >= 1.2 * d.vol_base) if 'volume' in d else pd.Series(True, index=d.index)
    long_break = up & bullish & volok & (d.close > d.prior_high + 0.15 * d.atr)
    short_break = down & bearish & volok & (d.close < d.prior_low - 0.15 * d.atr)
    touched_long = ((d.low.shift(1) <= d.ema20.shift(1) + 0.15 * d.atr.shift(1)) |
                    (d.low.shift(2) <= d.ema20.shift(2) + 0.15 * d.atr.shift(2)) |
                    (d.low.shift(3) <= d.ema20.shift(3) + 0.15 * d.atr.shift(3)))
    touched_short = ((d.high.shift(1) >= d.ema20.shift(1) - 0.15 * d.atr.shift(1)) |
                     (d.high.shift(2) >= d.ema20.shift(2) - 0.15 * d.atr.shift(2)) |
                     (d.high.shift(3) >= d.ema20.shift(3) - 0.15 * d.atr.shift(3)))
    long_pull = up & bullish & touched_long & (d.close > d.high.shift(1)) & (d.close > d.ema20) & (d.close <= d.prior_high + 0.5 * d.atr)
    short_pull = down & bearish & touched_short & (d.close < d.low.shift(1)) & (d.close < d.ema20) & (d.close >= d.prior_low - 0.5 * d.atr)
    atr_ok = (d.atr > 0) & ((d.atr / d.close).between(0.00005, 0.08))
    d['direction'] = np.select([atr_ok & (long_break | long_pull), atr_ok & (short_break | short_pull)], [1, -1], default=0)
    d['setup'] = np.select([atr_ok & long_break, atr_ok & short_break, atr_ok & long_pull, atr_ok & short_pull],
                           ['breakout_long', 'breakout_short', 'pullback_long', 'pullback_short'], default='none')
    d.loc[:55, ['direction', 'setup']] = [0, 'none']
    d['_up'], d['_down'], d['_volok'], d['_atr_ok'] = up, down, volok, atr_ok
    return d


SETUP_TEXT = {
    "breakout_long": "Breakout long: uptrend (EMA20 > EMA50, EMA20 rising), strong bullish candle, volume >= 1.2x the 20-bar median, close above the prior 20-bar high + 0.15 ATR.",
    "pullback_long": "Pullback long: uptrend, price touched EMA20 within the last 3 bars, strong bullish candle closing above the previous high and EMA20.",
    "breakout_short": "Breakout short: downtrend, strong bearish candle, volume confirmation, close below the prior 20-bar low - 0.15 ATR.",
    "pullback_short": "Pullback short: downtrend, price touched EMA20 within the last 3 bars, strong bearish candle closing below the previous low and EMA20.",
}


def evaluate(candles):
    """candles: oldest-first dicts with time/open/high/low/close/volume (closed bars only)."""
    if len(candles) <= WARMUP_BARS:
        return {"action": "HOLD", "setup": "none", "reasons": [f"Not enough closed candles ({len(candles)}); need more than {WARMUP_BARS}."], "indicators": {}}
    d = generate(pd.DataFrame(candles))
    last = d.iloc[-1]
    ind = {k: round(float(last[k]), 8) for k in ("close", "ema20", "ema50", "atr", "prior_high", "prior_low")}
    ind["volume"], ind["volume_median20"] = round(float(last["volume"]), 8), round(float(last["vol_base"]), 8)
    setup = str(last["setup"])
    if setup != "none":
        reasons = [SETUP_TEXT[setup]]
        action = "BUY" if int(last["direction"]) > 0 else "SELL"
    else:
        action = "HOLD"
        trend = "up" if bool(last["_up"]) else "down" if bool(last["_down"]) else "none (EMA20/EMA50 not aligned)"
        reasons = [f"No setup on the last closed candle. Trend: {trend}."]
        if not bool(last["_atr_ok"]):
            reasons.append("Volatility filter failed (ATR/close outside 0.005%-8%).")
        if not bool(last["_volok"]):
            reasons.append("Volume below 1.2x the 20-bar median.")
    return {"action": action, "setup": setup, "reasons": reasons, "indicators": ind,
            "candle_time": candles[-1]["time"]}
