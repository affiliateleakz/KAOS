"""Explainable KAOS market-research assessment from closed candles and evidence.

No calibrated price probability, actionable option contract, or order authority.
All derived values are point-in-time descriptors; fail closed on weak coverage.
"""
import math
from datetime import datetime,timezone

def ema(values,period):
    alpha=2/(period+1)
    value=values[0]
    for x in values[1:]:
        value=alpha*x+(1-alpha)*value
    return value

def rsi(values,period=14):
    changes=[b-a for a,b in zip(values,values[1:])]
    if len(changes)<period:return None
    gains=sum(max(x,0) for x in changes[-period:])/period
    losses=sum(max(-x,0) for x in changes[-period:])/period
    if losses==0:return 100. if gains else 50.
    return 100.-100./(1.+gains/losses)

def atr(rows,period=14):
    if len(rows)<period+1:return None
    tr=[]
    for prev,cur in zip(rows,rows[1:]):
        tr.append(max(cur["high"]-cur["low"],
                      abs(cur["high"]-prev["close"]),
                      abs(cur["low"]-prev["close"])))
    return sum(tr[-period:])/period

def assess(candles,evidence,*,symbol,asset_class,seconds,source,now_ms=None):
    if now_ms is None:now_ms=int(datetime.now(timezone.utc).timestamp()*1000)
    if not isinstance(candles,list):raise ValueError("missing candle sample")
    ordered=sorted(candles,key=lambda x:x["ts"])
    if any(r.get("symbol")!=symbol or r.get("asset_class")!=asset_class or
           r.get("seconds")!=seconds or r.get("source")!=source for r in ordered):
        raise ValueError("mixed asset or source")
    complete=[r for r in ordered if r["ts"]+seconds*1000<=now_ms]
    recent=complete[-200:]
    gaps=sum(b["ts"]-a["ts"]!=seconds*1000 for a,b in zip(recent,recent[1:]))
    coverage={
        "closed_candles":len(complete),"sampled_candles":len(recent),
        "gaps_in_sample":gaps,"full_history_available":False,
        "reason":"On-demand provider history is bounded; permanent archives not yet connected",
    }
    if len(recent)<55:
        return {"status":"insufficient_market_history","bias":"unknown","score":None,
                "score_type":"not_available","confidence":None,
                "buy_sell":"WAIT","coverage":coverage,
                "indicators":{},"patterns":[],"evidence":[],
                "target_price":None,"options":{"call_put":"NONE","expiry":None,"contract":None,
                "reason":"Insufficient price data and no verified options chain"},
                "research_only":True}
    closes=[float(r["close"]) for r in recent]
    highs=[float(r["high"]) for r in recent]
    lows=[float(r["low"]) for r in recent]
    if min(closes)<=0 or any(not math.isfinite(x) for x in closes+highs+lows):
        raise ValueError("invalid price history")
    e20=ema(closes[-100:],20)
    e50=ema(closes[-150:],50)
    macd=ema(closes[-100:],12)-ema(closes[-100:],26)
    rs=rsi(closes)
    av=atr(recent)
    last=recent[-1]["close"]
    vol_recent=[x.get("volume") for x in recent[-21:]]
    volume_ratio=None
    if all(isinstance(x,(int,float)) and math.isfinite(x) and x>=0 for x in vol_recent):
        avg=sum(vol_recent[:-1])/20
        volume_ratio=vol_recent[-1]/avg if avg else None
    price_votes=[
        1 if last>e20 else -1,
        1 if e20>e50 else -1,
        1 if macd>0 else -1,
        1 if rs is not None and rs>55 else -1 if rs is not None and rs<45 else 0,
    ]
    pattern=[]
    high_prior=max(highs[-21:-1]);low_prior=min(lows[-21:-1])
    if last>high_prior:pattern.append("20-bar high breakout")
    if last<low_prior:pattern.append("20-bar low breakdown")
    body=abs(recent[-1]["close"]-recent[-1]["open"])
    rng=recent[-1]["high"]-recent[-1]["low"]
    if rng>0 and body/rng<.08:pattern.append("Doji-like small body")
    if last>high_prior:price_votes.append(1)
    elif last<low_prior:price_votes.append(-1)
    else:price_votes.append(0)
    price_signal=sum(price_votes)
    # Exclude neutral headlines, and never treat an unverified news headline as
    # a causally confirmed price signal. Summarize independent source coverage.
    recent_evidence=[]
    seen=set()
    for rec in sorted(evidence,key=lambda r:str(r.get("observed_at","")),reverse=True):
        key=(rec.get("source"),rec.get("event_id"))
        if key in seen or len(recent_evidence)>=30:continue
        seen.add(key)
        recent_evidence.append({
            "source":rec.get("source"),"direction":rec.get("direction","neutral"),
            "summary":str(rec.get("summary",""))[:300],
            "observed_at":rec.get("observed_at"),
            "source_url":rec.get("source_url")
        })
    buckets={x["source"] for x in recent_evidence if x["source"]}
    signal_sum=sum(price_votes)
    # A heuristic directional index for RESEARCH ONLY. Not a calibrated
    # probability or trade signal. 50 is neutral.
    index=round(max(0,min(100,50+10*signal_sum)),1)
    fresh=(now_ms-(recent[-1]["ts"]+seconds*1000))<=max(seconds*1000*3,600000)
    if gaps or not fresh:
        direction="unknown";decision="WAIT";reason="Gaps or stale current price history"
    elif abs(signal_sum)<2:
        direction="mixed";decision="WAIT";reason="Technical evidence lacks agreement"
    else:
        direction="bullish" if signal_sum>0 else "bearish"
        decision="RESEARCH_BULLISH" if signal_sum>0 else "RESEARCH_BEARISH"
        reason="Technical indicators agree, but forecast performance is not calibrated"
    # A wider high/low scenario range is not a statistically estimated target.
    scenario=(None if av is None else {"atr_up_reference":round(last+av,6),
                 "atr_down_reference":round(max(.0000001,last-av),6),
                 "description":"Historical ATR distance references, NOT predicted target prices"})
    return {
        "status":"technical_research_only","symbol":symbol,"asset_class":asset_class,
        "seconds":seconds,"source":source,"as_of_ms":recent[-1]["ts"]+seconds*1000,
        "bias":direction,"buy_sell":decision,"score":index,
        "score_type":"uncalibrated_technical_alignment_index_not_win_probability",
        "confidence":None,"target_price":None,"scenario":scenario,
        "coverage":{**coverage,"fresh_closed_candles":fresh,
                    "source_categories_with_observations":sorted(buckets),
                    "missing_sources":[s for s in ("news","social","filing","insider","options_flow")
                                       if s not in buckets]},
        "indicators":{"last_close":last,"ema20":round(e20,6),
                      "ema50":round(e50,6),"rsi14":None if rs is None else round(rs,2),
                      "macd_12_26":round(macd,6),"atr14":None if av is None else round(av,6),
                      "volume_ratio_20":None if volume_ratio is None else round(volume_ratio,3)},
        "patterns":pattern,"evidence":recent_evidence,"reason":reason,
        "options":{"call_put":"NONE","expiry":None,"contract":None,
          "reason":"No verified option chain, strike, bid/ask, Greeks, liquidity, or expiration calendar; directional research is not a contract recommendation"},
        "research_only":True,"orders_enabled":False,
        "limitations":"No validated prediction model, no statistical price target, no live trade signal.",
    }
