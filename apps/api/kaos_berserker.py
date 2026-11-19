"""Legacy C9.0 two-candle research implementation, retained for old data compatibility.

The current KAOS Strategy execution authority is SR1.1 in kaos_signature.py,
matching apps/extension/candidate7b_strategy.js. This module is not the current bot.
"""
from __future__ import annotations
import math

CFG = {"name": "KAOS_BERSERKER", "version": "C9.0", "tf": 5, "expiry": 45,
       "emaFast": 9, "emaSlow": 21, "trendBars": 6, "minTrendBars": 4,
       "maxPullbackAtr": 1.35, "minConfirmBodyFrac": 0.45, "atrBars": 20}


def ema(a, p):
    if not a:
        return float("nan")
    k = 2 / (p + 1)
    e = a[0]
    for x in a[1:]:
        e = x * k + e * (1 - k)
    return e


def atr(q, p):
    s = q[-p:]
    if len(s) < 2:
        return float("nan")
    z = 0.0
    for i in range(1, len(s)):
        x, pc = s[i], s[i - 1]["close"]
        z += max(x["high"] - x["low"], abs(x["high"] - pc), abs(x["low"] - pc))
    return z / (len(s) - 1)


def aggregate(rows, sec):
    ms = sec * 1000
    out, b = [], None
    for r in rows:
        ts = int(r.get("ts") or r.get("closeTs") or 0)
        k = (ts // ms) * ms if ms else ts
        if b is None or b["ts"] != k:
            if b:
                out.append(b)
            b = {"ts": k, "open": float(r["open"]), "high": float(r["high"]),
                 "low": float(r["low"]), "close": float(r["close"])}
        else:
            b["high"] = max(b["high"], float(r["high"]))
            b["low"] = min(b["low"], float(r["low"]))
            b["close"] = float(r["close"])
    if b:
        out.append(b)
    return out


def body_frac(c):
    return abs(c["close"] - c["open"]) / max(1e-12, c["high"] - c["low"])


def signal(rows):
    """Return the raw Berserker signal dict or None (mirrors candidate7b_strategy.js `signal`)."""
    q = aggregate(rows, CFG["tf"])
    if len(q) < 50:
        return None
    c, p1, p2, p3 = q[-1], q[-2], q[-3], q[-4]
    pre = q[-3 - CFG["trendBars"]:-3]
    if len(pre) < CFG["trendBars"]:
        return None
    closes = [x["close"] for x in q]
    ef = ema(closes[-35:], CFG["emaFast"])
    es = ema(closes[-45:], CFG["emaSlow"])
    av = atr(q, CFG["atrBars"])
    if not math.isfinite(av) or av <= 0:
        return None
    greens = sum(1 for x in pre if x["close"] > x["open"])
    reds = sum(1 for x in pre if x["close"] < x["open"])
    bull_trend = ef > es and greens >= CFG["minTrendBars"] and pre[-1]["close"] > pre[0]["close"]
    bear_trend = ef < es and reds >= CFG["minTrendBars"] and pre[-1]["close"] < pre[0]["close"]
    pull_range = max(p1["high"], p2["high"]) - min(p1["low"], p2["low"])
    controlled = pull_range <= CFG["maxPullbackAtr"] * av
    if not controlled or body_frac(c) < CFG["minConfirmBodyFrac"]:
        return None
    # EXACTLY TWO counter-trend pullback candles: p2 (q[-3]) and p1 (q[-2]) are the pullback;
    # the candle immediately preceding them (p3 = q[-4]) MUST NOT continue that pullback, otherwise
    # the counter-trend sequence would be 3+ long and the Berserker setup is invalidated.
    p3_red = p3["close"] < p3["open"]
    p3_green = p3["close"] > p3["open"]
    if (bull_trend and p2["close"] < p2["open"] and p1["close"] < p1["open"] and not p3_red
            and c["close"] > c["open"] and c["close"] > p1["high"] and c["close"] > ef):
        return {"engine": "KAOS_BERSERKER", "internalId": "TWO_CANDLE_CONTINUATION",
                "direction": "BUY", "expiration": "45s", "confidence": 0.72,
                "strategyVersion": CFG["version"],
                "reason": "bull trend · exactly 2 red pullback candles · controlled retrace · bullish confirmation breaks pullback high · next-candle continuation"}
    if (bear_trend and p2["close"] > p2["open"] and p1["close"] > p1["open"] and not p3_green
            and c["close"] < c["open"] and c["close"] < p1["low"] and c["close"] < ef):
        return {"engine": "KAOS_BERSERKER", "internalId": "TWO_CANDLE_CONTINUATION",
                "direction": "SELL", "expiration": "45s", "confidence": 0.72,
                "strategyVersion": CFG["version"],
                "reason": "bear trend · exactly 2 green pullback candles · controlled retrace · bearish confirmation breaks pullback low · next-candle continuation"}
    return None


def evaluate(rows):
    """Public entry used by the server strategy boundary. Returns a single signal or None."""
    if not rows or len(rows) < 50:
        return None
    norm = []
    for x in rows:
        norm.append({"ts": int(x.get("ts") or x.get("closeTs") or 0),
                     "open": float(x["open"]), "high": float(x["high"]),
                     "low": float(x["low"]), "close": float(x["close"])})
    norm.sort(key=lambda r: r["ts"])
    return signal(norm)
