"""KAOS Trend-Pause v1: deterministic closed-candle CALL/PUT research signals.

Rules: 1m EMA20/50 aligned and sloped over three 1m closes; 15s EMA20;
1-3 contrary pause candles followed by closed breakout confirmation.
Intended signal entry at NEXT 15s candle open; default horizon 60s.
Research-only: no execution, profitability claims, or synthetic fills.
"""
from math import isfinite

def ema(values, period):
    if len(values) < period:
        return None
    value = sum(values[:period]) / period
    out = [None] * (period - 1) + [value]
    alpha = 2 / (period + 1)
    for price in values[period:]:
        value = alpha * price + (1 - alpha) * value
        out.append(value)
    return out

def validate(candles):
    if not isinstance(candles, list):
        raise ValueError("Candle list required")
    times = set()
    previous = None
    cleaned = []
    for c in candles:
        try:
            ts = int(c["ts"])
            o,h,l,close = (float(c[k]) for k in ("open","high","low","close"))
        except (KeyError,TypeError,ValueError,OverflowError):
            raise ValueError("Invalid OHLC candle") from None
        if not all(isfinite(v) for v in (o,h,l,close)) or min(o,h,l,close) <= 0 or l > min(o,close) or h < max(o,close):
            raise ValueError("Invalid OHLC price")
        if previous is not None and ts <= previous:
            raise ValueError("Candles must be strictly increasing without duplicate timestamps")
        times.add(ts); previous = ts
        cleaned.append({"ts": ts,"open":o,"high":h,"low":l,"close":close})
    return cleaned

def signal(one_minute, fifteen_seconds):
    """Return one setup at most. Both lists MUST contain completed, chronological candles.

    The one-minute candles must be closed by the 15s confirmation end time.
    For a candle whose ts is its opening time, 1m bars close at ts+60_000.
    No use of incomplete current 1m candle or future values.
    """
    m = validate(one_minute)
    q = validate(fifteen_seconds)
    if len(m) < 53 or len(q) < 24:
        return None
    confirm = q[-1]
    cutoff = confirm["ts"] + 15000
    m = [bar for bar in m if bar["ts"] + 60000 <= cutoff]
    if len(m) < 53:
        return None
    twenty = ema([x["close"] for x in m],20)
    fifty = ema([x["close"] for x in m],50)
    qtwenty = ema([x["close"] for x in q],20)
    if any(x is None for x in (twenty[-1],twenty[-4],fifty[-1],fifty[-4],qtwenty[-1])):
        return None
    latest=m[-1]["close"]
    bullish=(latest>twenty[-1]>fifty[-1] and twenty[-1]>twenty[-4] and fifty[-1]>fifty[-4])
    bearish=(latest<twenty[-1]<fifty[-1] and twenty[-1]<twenty[-4] and fifty[-1]<fifty[-4])
    if not bullish and not bearish:
        return None
    if bullish and not (confirm["close"]>confirm["open"] and confirm["close"]>qtwenty[-1]):
        return None
    if bearish and not (confirm["close"]<confirm["open"] and confirm["close"]<qtwenty[-1]):
        return None
    # Select the longest 1-3 immediately preceding pause sequence, without guessing an entry.
    for count in (3,2,1):
        pause=q[-count-1:-1]
        if len(pause)!=count:
            continue
        before=q[-count-2]
        if bullish:
            counter=all(pause[i]["close"] <= (before if i==0 else pause[i-1])["close"] for i in range(count))
            breakout=confirm["close"]>max(x["high"] for x in pause)
            support=all(x["low"]>=twenty[-1] for x in pause)
            direction="CALL"
        else:
            counter=all(pause[i]["close"] >= (before if i==0 else pause[i-1])["close"] for i in range(count))
            breakout=confirm["close"]<min(x["low"] for x in pause)
            support=all(x["high"]<=twenty[-1] for x in pause)
            direction="PUT"
        if counter and breakout and support:
            return {"strategy":"KAOS_TREND_PAUSE_V1","direction":direction,
                    "confirmation_ts":confirm["ts"],"entry_rule":"NEXT_15S_OPEN",
                    "horizon_seconds":60,"pause_candles":count,
                    "source":"closed_1m_and_15s_candles","trade_executable":False}
    return None
