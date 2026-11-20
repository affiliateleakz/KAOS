"""Independent KAOS historical price-structure similarity search.

Closed OHLCV only; no screenshots or predicted probabilities. Similarity is a
descriptive nearest-neighbor measure, not calibrated predictive confidence.
"""
import math

PATTERN_TAGS = ("uptrend", "downtrend", "range", "breakout_up", "breakout_down")
PATTERN_UNKNOWN = "unknown"


def classify_pattern(segment):
    """Deterministic market structure tag from completed OHLCV candles only.

    This is a rough structural classification, not a validated pattern detector.
    """
    if len(segment) < 10:
        return PATTERN_UNKNOWN
    previous = segment[:-1]
    last = segment[-1]
    # Use completed prior bar extrema for breakout context; no future prices.
    prev_high = max(c["high"] for c in previous[-10:])
    prev_low = min(c["low"] for c in previous[-10:])
    if last["close"] > prev_high:
        return "breakout_up"
    if last["close"] < prev_low:
        return "breakout_down"
    close_earlier = previous[0]["close"]
    relative = last["close"] / close_earlier - 1.
    if relative >= .01:
        return "uptrend"
    if relative <= -.01:
        return "downtrend"
    return "range"

def compare(rows, lookback=20, horizon=5, limit=5, pattern=None):
    if not (5 <= lookback <= 60 and 1 <= horizon <= 60 and 1 <= limit <= 10):
        raise ValueError("invalid lookback, horizon, or limit")
    if pattern is not None and pattern not in PATTERN_TAGS:
        raise ValueError("unsupported historical pattern label")
    if len(rows) < lookback * 3 + horizon + 2:
        return {"matches": [], "count": 0, "reason": "insufficient archived candle history"}
    bars = sorted(rows, key=lambda r: r["ts"])
    sources = {(b.get("symbol"), b.get("source"), b.get("seconds")) for b in bars}
    if len(sources) != 1 or None in next(iter(sources)):
        raise ValueError("mixed candle sources")
    interval = bars[0]["seconds"] * 1000
    if interval <= 0:
        raise ValueError("invalid interval")
    for b in bars:
        vals = [b.get(k) for k in ("open", "high", "low", "close", "volume")]
        if any(type(x) not in (int, float) or not math.isfinite(x) for x in vals):
            raise ValueError("invalid OHLCV")
        if min(vals[:4]) <= 0 or vals[4] < 0 or b["low"] > min(b["open"], b["close"]) or b["high"] < max(b["open"], b["close"]):
            raise ValueError("invalid OHLCV")
    def contiguous(a, b):
        return all(bars[k+1]["ts"] - bars[k]["ts"] == interval for k in range(a, b))
    last = len(bars)-1
    if not contiguous(last-lookback+1, last):
        return {"matches": [], "count": 0, "reason": "latest chart has missing candles"}

    def shape(end):
        start = end-lookback+1
        base = bars[start]["close"]
        seq = [math.log(bars[k]["close"]/base) for k in range(start,end+1)]
        scale = max(math.sqrt(sum(v*v for v in seq)/len(seq)), .002)
        return [v/scale for v in seq]
    target = shape(last)
    current_tag = classify_pattern(bars[last-lookback+1:last+1])
    candidates=[]
    for end in range(lookback-1, last-lookback-horizon):
        if not contiguous(end-lookback+1, end+horizon):
            continue
        candidate_tag = classify_pattern(bars[end-lookback+1:end+1])
        if pattern is not None and candidate_tag != pattern:
            continue
        arr=shape(end)
        distance=math.sqrt(sum((a-b)**2 for a,b in zip(arr,target))/lookback)
        entry=bars[end+1]["open"]
        after=bars[end+horizon]["close"]
        candidates.append({"distance": round(distance,5), "decision_ms":bars[end]["ts"]+interval,
                           "outcome_ms":bars[end+horizon]["ts"]+interval,
                           "forward_return_proxy": round(after/entry-1,8),
                           "pattern":candidate_tag})
    candidates.sort(key=lambda c:c["distance"])
    chosen=[]
    for c in candidates:
        if all(abs(c["decision_ms"]-m["decision_ms"])>=lookback*interval for m in chosen):
            chosen.append(c)
            if len(chosen)>=limit:
                break
    return {"matches": chosen, "count":len(chosen),
            "current_archived_pattern": current_tag,
            "requested_pattern": pattern,
            "match_basis": "screenshot_pattern_category_filter" if pattern else "latest_archived_price_shape",
            "historical_up_fraction": (sum(m["forward_return_proxy"]>0 for m in chosen)/len(chosen)) if chosen else None,
            "status":"historical_similarity_only",
            "note":"Nearest historical structures, no calibrated forecast, execution model, or trade signal."}
