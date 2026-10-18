"""LEGACY research strategy — the old Candidate 7B three-engine (REVERSAL/RUNNER/BREAKOUT) logic.

NOT the KAOS Berserker. The real signature strategy is in kaos_berserker.py. This module is kept
as separate research/legacy logic and must NOT be presented as, or silently execute as, Berserker.
"""
from __future__ import annotations
import math

# Backtest horizon buckets (ms) kept for reference; live expirations per B32.21.7 corrections.
ENGINE_EXPIRATION = {"REVERSAL": "30s", "RUNNER": "15s", "BREAKOUT": "30s"}
ENGINE_PRIORITY = {"REVERSAL": 0, "BREAKOUT": 1, "RUNNER": 2}


def ema(a, p):
    if not a:
        return float("nan")
    e = a[0]
    k = 2 / (p + 1)
    for x in a[1:]:
        e = x * k + e * (1 - k)
    return e


def atr(q, p=14):
    tr = []
    for i in range(1, len(q)):
        c = q[i]
        pc = q[i - 1]["close"]
        tr.append(max(c["high"] - c["low"], abs(c["high"] - pc), abs(c["low"] - pc)))
    s = tr[-p:]
    return sum(s) / len(s) if s else float("nan")


def aggregate(rows, sec):
    out = []
    b = None
    ms = sec * 1000
    for r in rows:
        ts = int(r.get("ts") or r.get("closeTs") or 0)
        k = ts // ms * ms if ms else ts
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


def _norm(rows):
    """Coerce raw candle rows to sorted numeric OHLC with a ts field."""
    out = []
    for x in rows:
        ts = int(x.get("ts") or x.get("closeTs") or 0)
        out.append({"ts": ts, "open": float(x["open"]), "high": float(x["high"]),
                    "low": float(x["low"]), "close": float(x["close"])})
    return sorted(out, key=lambda r: r["ts"])


# ----- Engine 1: REVERSAL (30s structure, SELL only failed-break rejection) -----
def reversal(rows):
    q = aggregate(rows, 30)
    if len(q) < 10:
        return None
    cur = q[-1]
    pr = q[-9:-1]
    lv = max(x["high"] for x in pr)
    rg = max(1e-12, cur["high"] - cur["low"])
    uw = (cur["high"] - max(cur["open"], cur["close"])) / rg
    if cur["high"] > lv and cur["close"] < lv and cur["close"] < cur["open"] and uw >= 0.35 and body_frac(cur) >= 0.15:
        return {"engine": "REVERSAL", "direction": "SELL", "expiration": ENGINE_EXPIRATION["REVERSAL"],
                "confidence": 0.70,
                "reason": "failed-break rejection above prior resistance · bearish close · >=35% upper wick"}
    return None


# ----- Engine 2: RUNNER (5s structure, first-pullback continuation) -----
def runner(rows):
    q = rows
    if len(q) < 35:
        return None
    cur, prev = q[-1], q[-2]
    cl = [x["close"] for x in q]
    av = atr(q)
    if not av or not math.isfinite(av):
        return None
    e9 = ema(cl, 9)
    e21 = ema(cl, 21)
    score = min(1.0, abs(e9 - e21) / av)
    ext = abs(cur["close"] - e9) / av
    mn = (cur["close"] - q[-4]["close"]) / av
    mp = (prev["close"] - q[-5]["close"]) / av
    d = None
    if e9 > e21 and cur["close"] > cur["open"] and prev["close"] <= prev["open"] and mn > mp:
        d = "BUY"
    if e9 < e21 and cur["close"] < cur["open"] and prev["close"] >= prev["open"] and mn < mp:
        d = "SELL"
    if d and score >= 0.70 and body_frac(cur) >= 0.50 and ext <= 1.10:
        return {"engine": "RUNNER", "direction": d, "expiration": ENGINE_EXPIRATION["RUNNER"],
                "confidence": round(0.60 + 0.30 * score, 2),
                "reason": "EMA9/21 trend · first counter pullback · same-trend resumption body>=50% · momentum re-accelerates"}
    return None


# ----- Engine 3: BREAKOUT (15s structure, confirmed break + hold/retest) -----
def breakout(rows):
    q = aggregate(rows, 15)
    if len(q) < 22:
        return None
    av = atr(q)
    ret, br = q[-1], q[-2]
    pr = q[-8:-2]
    hi = max(x["high"] for x in pr)
    lo = min(x["low"] for x in pr)
    if not av or (hi - lo) / av > 0.75:
        return None
    bu = br["close"] >= hi + 0.10 * av and br["close"] > br["open"] and body_frac(br) >= 0.50
    bd = br["close"] <= lo - 0.10 * av and br["close"] < br["open"] and body_frac(br) >= 0.50
    if bu and ret["low"] >= hi - 0.12 * av and ret["close"] > hi and ret["close"] > ret["open"]:
        return {"engine": "BREAKOUT", "direction": "BUY", "expiration": ENGINE_EXPIRATION["BREAKOUT"],
                "confidence": 0.70, "reason": "confirmed breakout above level · retest holds · close back outside level"}
    if bd and ret["high"] <= lo + 0.12 * av and ret["close"] < lo and ret["close"] < ret["open"]:
        return {"engine": "BREAKOUT", "direction": "SELL", "expiration": ENGINE_EXPIRATION["BREAKOUT"],
                "confidence": 0.70, "reason": "confirmed breakdown below level · retest holds · close back outside level"}
    return None


def evaluate(rows):
    """Run all three engines and apply conflict/priority resolution.

    Returns the single chosen signal dict, or None when there is no confirmed setup or an
    opposite-direction conflict blocks the trade.
    """
    if not rows or len(rows) < 10:
        return None
    q = _norm(rows)
    sigs = [s for s in (reversal(q), breakout(q), runner(q)) if s and s.get("direction")]
    if not sigs:
        return None
    dirs = {s["direction"] for s in sigs}
    if len(dirs) > 1:
        return None  # opposite-direction simultaneous engines => NO TRADE
    chosen = sorted(sigs, key=lambda s: ENGINE_PRIORITY[s["engine"]])[0]
    if len(sigs) > 1:
        chosen = {**chosen, "overlap": [s["engine"] for s in sigs]}
    return chosen
