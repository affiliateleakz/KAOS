"""Observe Codex candlestick patterns on *all* archived candles, even without trades.

Pattern detection uses only candles available at observation timestamp.
Historical outcomes use later CLOSED candles and never bridge missing bars.
This is independent research telemetry: no strategies, broker orders or AI promotion.
"""
import hashlib
from collections import Counter
from kaos_candlestick_patterns import scan, catalog

HORIZONS=(1,4,10)

def _segments(rows, seconds):
    if seconds not in (60,300,900):
        raise ValueError("Unsupported timeframe")
    delta=seconds*1000
    segments=[]
    segment=[]
    for r in rows:
        if segment and r["ts"]<=segment[-1]["ts"]:
            raise ValueError("Candles must be strictly chronological")
        if segment and r["ts"]-segment[-1]["ts"]!=delta:
            segments.append(segment)
            segment=[]
        segment.append(r)
    if segment:
        segments.append(segment)
    return segments

def observe_market(rows, symbol, asset_class, seconds=60, source=None,
                   *, max_patterns_per_segment=500):
    if not isinstance(rows,list) or len(rows)>5000:
        raise ValueError("Expected <=5000 archived candles")
    if not isinstance(max_patterns_per_segment,int) or not 1<=max_patterns_per_segment<=500:
        raise ValueError("Invalid pattern scan limit")
    events=[]
    segments=_segments(rows,seconds)
    for segment_idx,bars in enumerate(segments):
        matches=scan(bars,max_patterns=max_patterns_per_segment)
        for m in matches:
            i=m["index"]
            candle=bars[i]
            observations=[]
            for horizon in HORIZONS:
                future_idx=i+horizon
                if future_idx>=len(bars):
                    observations.append({"horizon_bars":horizon,"status":"pending"})
                    continue
                end=bars[future_idx]
                price0=float(candle["close"])
                price1=float(end["close"])
                actual="UP" if price1>price0 else "DOWN" if price1<price0 else "TIE"
                predicted={"bullish":"UP","bearish":"DOWN"}.get(m["direction"])
                observations.append({
                    "horizon_bars":horizon,"status":"settled",
                    "settlement_ts":end["ts"],"settlement_close":price1,
                    "direction":actual,"return_pct":round(100*(price1/price0-1),6),
                    "correct":actual==predicted if predicted and actual!="TIE" else None,
                })
            event_key="|".join([str(source or ""),asset_class,symbol,str(seconds),
                                str(candle["ts"]),m["pattern"],m["direction"]])
            eid=hashlib.sha256(event_key.encode("utf-8")).hexdigest()[:32]
            events.append({
                "id":eid,"symbol":symbol,"asset_class":asset_class,"seconds":seconds,
                "source":source,"observed_ts":candle["ts"],
                "pattern":m["pattern"],"direction":m["direction"],
                "method":m["method"],"close":float(candle["close"]),
                "segment_index":segment_idx,
                "horizons":observations,
                "research_only":True,"execution_enabled":False,
                "based_on_trades":False,
            })
    totals=Counter(x["pattern"] for x in events)
    return {
        "symbol":symbol,"asset_class":asset_class,"source":source,
        "seconds":seconds,"bars":len(rows),"segments":len(segments),
        "catalog_count":len(catalog()),
        "implemented_count":sum(c["implemented"] for c in catalog()),
        "events_count":len(events),
        "pattern_counts":dict(totals),
        "events":events,
        "research_only":True,"execution_enabled":False,
        "based_on_trades":False,
    }
