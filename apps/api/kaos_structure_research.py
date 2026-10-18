"""Deterministic closed-candle price-action research signals; no order routing.

Uses only the last completed bar, with an explicit lookback. Priority:
failed breakout reversal, break-and-retest, pullback continuation, breakout.
"""
from kaos_trend_pause import validate

def signal(candles, *, lookback=12):
    bars=validate(candles)
    if not 5<=lookback<=100 or len(bars)<lookback+4:
        return None
    prior=bars[-(lookback+2):-2]
    prev,now=bars[-2:]
    resistance=max(x["high"] for x in prior)
    support=min(x["low"] for x in prior)
    body=abs(now["close"]-now["open"])
    mid=(now["high"]+now["low"])/2
    # Reversal: prior close crossed the range but latest candle rejected it.
    if prev["close"]>resistance and now["close"]<resistance and now["close"]<mid and body>0:
        return {"setup":"FAILED_BREAKOUT_REVERSAL","direction":"PUT","level":resistance}
    if prev["close"]<support and now["close"]>support and now["close"]>mid and body>0:
        return {"setup":"FAILED_BREAKOUT_REVERSAL","direction":"CALL","level":support}
    # Retest: prior candle closes beyond the boundary, then latest candle
    # touches that boundary and closes back in the breakout direction.
    if prev["close"]>resistance and now["low"]<=resistance and now["close"]>resistance:
        return {"setup":"BREAKOUT_RETEST","direction":"CALL","level":resistance}
    if prev["close"]<support and now["high"]>=support and now["close"]<support:
        return {"setup":"BREAKOUT_RETEST","direction":"PUT","level":support}
    # Trend continuation after an opposing close, then confirmation.
    slope=prior[-1]["close"]-prior[0]["close"]
    if slope>0 and prev["close"]<prev["open"] and now["close"]>prev["high"] and now["close"]>now["open"]:
        return {"setup":"PULLBACK_CONTINUATION","direction":"CALL","level":prev["high"]}
    if slope<0 and prev["close"]>prev["open"] and now["close"]<prev["low"] and now["close"]<now["open"]:
        return {"setup":"PULLBACK_CONTINUATION","direction":"PUT","level":prev["low"]}
    if now["close"]>resistance and prev["close"]<=resistance and now["close"]>now["open"]:
        return {"setup":"BREAKOUT","direction":"CALL","level":resistance}
    if now["close"]<support and prev["close"]>=support and now["close"]<now["open"]:
        return {"setup":"BREAKOUT","direction":"PUT","level":support}
    return None
