"""Leakage-safe multi-timeframe chart context for KAOS shadow research."""
from math import isfinite
from multi_horizon_dataset import instant

def features_at(candles, decision_at, *, periods=(5, 15, 30, 60, 300, 900), lookback=24):
    """Analyze bars whose close timestamps precede a trading decision.

    Candle schema: symbol, source, seconds, ts (opening epoch milliseconds),
    OHLC. A timeframe with too few valid closed bars is omitted, not invented.
    """
    cutoff = instant(decision_at)
    if not 3 <= lookback <= 500:
        raise ValueError("Invalid lookback")
    result = {}
    for seconds in periods:
        if type(seconds) is not int or seconds <= 0:
            raise ValueError("Invalid timeframe")
        valid = []
        for bar in candles:
            if bar.get("seconds") != seconds or bar.get("simulated"):
                continue
            try:
                stamp = bar["ts"] / 1000 + seconds
                o,h,l,c = (float(bar[k]) for k in ("open","high","low","close"))
                if not all(isfinite(x) for x in (stamp,o,h,l,c)):
                    continue
                if stamp > cutoff or l <= 0 or l > min(o,c) or max(o,c) > h:
                    continue
                valid.append((stamp,o,h,l,c))
            except (KeyError,TypeError,ValueError,OverflowError):
                continue
        valid.sort(key=lambda x:x[0])
        # Repeated data must not overweight a particular candle.
        by_close = {row[0]:row for row in valid}
        recent = [by_close[k] for k in sorted(by_close)[-lookback:]]
        if len(recent) < 3:
            continue
        latest, prev = recent[-1], recent[-2]
        closes = [x[4] for x in recent]
        previous_high = max(x[2] for x in recent[:-1])
        previous_low = min(x[3] for x in recent[:-1])
        bullish = latest[4] > latest[1]
        bearish = latest[4] < latest[1]
        result[str(seconds)] = {
            "bars":len(recent),
            "trend_return":(closes[-1]/closes[0]-1),
            "up_closes":sum(b>a for a,b in zip(closes,closes[1:])),
            "down_closes":sum(b<a for a,b in zip(closes,closes[1:])),
            "bullish_engulfing":bullish and prev[4]<prev[1] and latest[1]<=prev[4] and latest[4]>=prev[1],
            "bearish_engulfing":bearish and prev[4]>prev[1] and latest[1]>=prev[4] and latest[4]<=prev[1],
            "breakout_high":latest[4]>previous_high,
            "breakout_low":latest[4]<previous_low,
            "inside_bar":latest[2]<=prev[2] and latest[3]>=prev[3],
            "last_body_fraction":abs(latest[4]-latest[1])/(latest[2]-latest[3]) if latest[2]>latest[3] else 0.0,
        }
    return result
