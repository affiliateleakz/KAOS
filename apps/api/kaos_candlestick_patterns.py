"""KAOS independently implemented, closed-candle pattern recognition library.

Pattern names are conventional technical-analysis vocabulary, not proprietary
source code. All detections are heuristic research annotations, never orders.
The catalog includes classic families; implemented rules are explicitly marked.
"""
import math

CATALOG = (
    "Hammer", "Shooting Star", "Bullish Engulfing", "Morning Star",
    "Evening Star", "Harami", "Hanging Man", "Doji", "Pin Bar",
    "Bullish Mat Hold", "Gap Up / Gap Down", "Tri Star",
    "Tweezer Top / Bottom", "Belt Hold", "Abandoned Baby", "Kicker",
    "Three Outside Up / Down", "Three Inside Up / Down", "Piercing Line",
    "Dark Cloud Cover", "Three Black Crows", "Rising Three Methods",
    "Falling Three Methods", "Tasuki Gap", "Inside Bar", "Outside Bar",
    "Spinning Top", "Popgun", "Shaven Head", "Shaven Bottom",
    "High Wave", "Separating Lines", "On Neck", "In Neck", "Breakaway",
    "Concealing Baby Swallow", "Homing Pigeon", "Ladder Bottom",
    "Ladder Top", "Matching High", "Matching Low", "Meeting Lines",
    "Bullish Side by Side White Lines", "Bullish Stick Sandwich",
    "Three Line Strike", "Unique Three River Bottom",
    "Three Stars in the South", "Advanced Block", "Deliberation",
    "Identical Three Crows",
)
# Unimplemented catalog names are educational placeholders, NOT detections.
IMPLEMENTED = frozenset((
    "Hammer", "Shooting Star", "Bullish Engulfing", "Morning Star",
    "Evening Star", "Harami", "Hanging Man", "Doji", "Pin Bar",
    "Gap Up / Gap Down", "Tweezer Top / Bottom", "Inside Bar",
    "Outside Bar", "Spinning Top", "Shaven Head", "Shaven Bottom",
    "Piercing Line", "Dark Cloud Cover", "Three Black Crows",
    "Rising Three Methods", "Falling Three Methods",
))
TREND_BARS = 4


def _candle(row):
    if not isinstance(row, dict):
        raise ValueError("invalid candle")
    vals = [row.get(k) for k in ("open", "high", "low", "close")]
    if any(type(v) not in (float, int) or not math.isfinite(v) for v in vals):
        raise ValueError("invalid OHLC")
    o, h, l, c = vals
    if min(vals) <= 0 or l > min(o,c) or h < max(o,c) or l > h:
        raise ValueError("inconsistent OHLC")
    return o,h,l,c


def scan(candles, *, max_patterns=50):
    """Detect a subset of classic formations on complete ordered bars.

    No future bars, no ML scores, no image inputs. Context rules use past
    closes; no gap-dependent assertion is made in sessionless OTC markets.
    """
    if not isinstance(candles, list) or len(candles) > 10000:
        raise ValueError("candles must be a bounded list")
    if not (type(max_patterns) is int and 1 <= max_patterns <= 500):
        raise ValueError("invalid max_patterns")
    if len(candles) < 5:
        return []
    bars=[_candle(b) for b in candles]
    results=[]
    def emit(name, index, direction, n=1, note=""):
        if name not in IMPLEMENTED:
            raise ValueError("unimplemented pattern")
        results.append({"pattern":name,"index":index,"start_index":index-n+1,
                        "direction":direction,"method":"closed_ohlc_heuristic_v1",
                        "note":note or "Heuristic pattern, not a trade signal"})
    def bullish(b):return b[3]>b[0]
    def bearish(b):return b[3]<b[0]
    def body(b):return abs(b[3]-b[0])
    def span(b):return max(b[1]-b[2],1e-12)
    def mid(b):return (b[0]+b[3])/2.
    def trend(i):
        # Context before current pattern; no lookahead.
        if i<4:return "none"
        a=bars[i-4][3];z=bars[i-1][3]
        if z>a*1.005:return "up"
        if z<a*.995:return "down"
        return "flat"
    for i in range(4,len(bars)):
        b=bars[i]; a=bars[i-1]; prev2=bars[i-2]
        rng=span(b);bd=body(b);upper=b[1]-max(b[0],b[3]);lower=min(b[0],b[3])-b[2]
        ctx=trend(i)
        if bd <= rng*.08:emit("Doji",i,"neutral")
        if bd <= rng*.3 and upper >= rng*.3 and lower >= rng*.3:
            emit("Spinning Top",i,"neutral")
        if lower>=2*max(bd,rng*.04) and upper<=rng*.18:
            if ctx=="down":emit("Hammer",i,"bullish")
            elif ctx=="up":emit("Hanging Man",i,"bearish")
            emit("Pin Bar",i,"bullish")
        if upper>=2*max(bd,rng*.04) and lower<=rng*.18:
            if ctx=="up":emit("Shooting Star",i,"bearish")
            emit("Pin Bar",i,"bearish")
        if upper<=rng*.025:emit("Shaven Head",i,"neutral")
        if lower<=rng*.025:emit("Shaven Bottom",i,"neutral")
        if b[1]<a[1] and b[2]>a[2]:emit("Inside Bar",i,"neutral",2)
        if b[1]>a[1] and b[2]<a[2]:emit("Outside Bar",i,"neutral",2)
        if bearish(a) and bullish(b) and b[0]<=a[3] and b[3]>=a[0] and body(b)>body(a):
            emit("Bullish Engulfing",i,"bullish",2)
        if body(b)<body(a)*.65 and min(a[0],a[3])<=min(b[0],b[3]) and max(b[0],b[3])<=max(a[0],a[3]):
            emit("Harami",i,"neutral",2)
        if bearish(a) and bullish(b) and b[3]>mid(a) and b[3]<a[0] and b[0]<=a[3]:
            emit("Piercing Line",i,"bullish",2)
        if bullish(a) and bearish(b) and b[3]<mid(a) and b[3]>a[0] and b[0]>=a[3]:
            emit("Dark Cloud Cover",i,"bearish",2)
        if abs(a[1]-b[1])/a[1]<=.001 and bullish(a) and bearish(b):
            emit("Tweezer Top / Bottom",i,"bearish",2)
        if abs(a[2]-b[2])/a[2]<=.001 and bearish(a) and bullish(b):
            emit("Tweezer Top / Bottom",i,"bullish",2)
        if b[2]>a[1] or b[1]<a[2]:
            emit("Gap Up / Gap Down",i,"bullish" if b[2]>a[1] else "bearish",2,
                 "Price gap; session and market structure require verification")
        if i>=2:
            x=prev2
            if bearish(x) and body(a)<body(x)*.35 and bullish(b) and b[3]>(x[0]+x[3])/2:
                emit("Morning Star",i,"bullish",3)
            if bullish(x) and body(a)<body(x)*.35 and bearish(b) and b[3]<(x[0]+x[3])/2:
                emit("Evening Star",i,"bearish",3)
            if (bearish(x) and bearish(a) and bearish(b) and
                x[3]>a[3]>b[3] and x[0]>a[0]>b[0] and
                all(body(t)>=.5*span(t) for t in (x,a,b))):
                emit("Three Black Crows",i,"bearish",3)
        if i>=4:
            seq=bars[i-4:i+1]
            if (bullish(seq[0]) and bullish(seq[4]) and
                all(body(t)<body(seq[0]) for t in seq[1:4]) and
                seq[4][3]>seq[0][1]):
                emit("Rising Three Methods",i,"bullish",5)
            if (bearish(seq[0]) and bearish(seq[4]) and
                all(body(t)<body(seq[0]) for t in seq[1:4]) and
                seq[4][3]<seq[0][2]):
                emit("Falling Three Methods",i,"bearish",5)
    return results[-max_patterns:]


def catalog():
    return [{"name":name,"implemented":name in IMPLEMENTED,
             "status":"heuristic_detectable" if name in IMPLEMENTED else "catalog_only"}
            for name in CATALOG]
