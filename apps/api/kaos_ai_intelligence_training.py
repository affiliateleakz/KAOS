"""Optional chronology-safe historical intelligence research model.

Only records already ingested to kaos_intelligence may be used. Each event's
observed_at AND published_at must predate the prediction feature cutoff.
No retrospectively fetched headline is allowed to leak into older labels.
This model is separate from R2 OHLC inference and cannot issue broker orders.
"""
from collections import deque
from datetime import datetime, timezone
from hashlib import sha256
from math import exp, isfinite, sqrt
import json

from kaos_r2_ai_lab import FEATURES, make_samples, _split, _evaluate, _sigmoid, _wilson_lower
from kaos_opportunity import SOURCES, utc

SCHEMA="kaos_r2_intelligence_logistic_v1"
KINDS=tuple(sorted(SOURCES))
FEATURE_NAMES=tuple(FEATURES)+tuple("evidence_"+x for x in KINDS)
LOOKBACK_MS=24*60*60*1000
MAX_RECORDS=3000


def normalize_events(raw, symbol, asset_class):
    if not isinstance(raw,list) or len(raw)>MAX_RECORDS:
        raise ValueError("Intelligence activity incomplete or exceeds bounded source cap")
    observations=[]
    seen=set()
    for row in raw:
        if not isinstance(row,dict) or row.get("asset")!=symbol or row.get("asset_class")!=asset_class:
            continue
        kind=row.get("source")
        side=row.get("direction")
        eid=row.get("event_id")
        if kind not in KINDS or side not in ("bullish","bearish","neutral"):
            continue
        if not isinstance(eid,str) or not eid or (kind,eid) in seen:
            continue
        try:
            observed=utc(row["observed_at"])
            published=utc(row["published_at"])
            strength=float(row["strength"])
        except (KeyError,TypeError,ValueError,OverflowError):
            continue
        if published>observed or not isfinite(strength) or not 0<strength<=1 or side=="neutral":
            continue
        seen.add((kind,eid))
        observations.append({
            "key":kind+":"+eid,
            "source":kind,
            "observed_ms":int(observed.timestamp()*1000),
            "published_ms":int(published.timestamp()*1000),
            "direction":side,
            # Neutral articles signal presence, not bullish/bearish strength.
            "vote":strength*(1 if side=="bullish" else -1 if side=="bearish" else 0),
        })
    observations.sort(key=lambda e:(e["observed_ms"],e["key"]))
    return observations


def join_asof_samples(rows,events,seconds,horizon):
    samples=make_samples(rows,seconds,horizon)
    if not samples:
        return [],{"event_count":len(events),"sample_coverage":0,
                   "source_counts":{},"distinct_matched_events":0}
    active=deque()
    idx=0
    total={k:0.0 for k in KINDS}
    count={k:0 for k in KINDS}
    hit=set()
    covered=0
    current_directional_count=0
    by_source={k:0 for k in KINDS}
    joined=[]
    # samples are chronological. Each feature cutoff is at candle CLOSE,
    # not its later settlement CLOSE.
    for sample in samples:
        cutoff=sample["ts"]+seconds*1000
        while idx<len(events) and events[idx]["observed_ms"]<=cutoff:
            event=events[idx];idx+=1
            if event["published_ms"]>cutoff:
                continue
            active.append(event)
            count[event["source"]]+=1
            total[event["source"]]+=event["vote"]
            if event["observed_ms"]>=cutoff-LOOKBACK_MS: hit.add(event["key"])
            current_directional_count+=1
        while active and active[0]["observed_ms"]<cutoff-LOOKBACK_MS:
            event=active.popleft()
            count[event["source"]]-=1
            total[event["source"]]-=event["vote"]
            current_directional_count-=1
        has_evidence=current_directional_count>0
        if has_evidence:
            covered+=1
            for key in KINDS:
                if count[key]>0:by_source[key]+=1
        # Scale to [-1,1], so a high-volume news source cannot dominate
        # the feature matrix just by repeating articles.
        vector=[max(-1.,min(1.,total[k]/count[k])) if count[k]>0 else 0.0
                for k in KINDS]
        joined.append({**sample,"x":list(sample["x"])+vector,
                       "has_external_evidence":has_evidence})
    return joined,{
        "event_count":len(events),
        "sample_coverage":round(covered/len(joined),4),
        "source_counts":{k:count for k,count in by_source.items() if count>0},
        "distinct_matched_events":len(hit),
    }


def _fit_variable(train,epochs=120):
    n=len(train)
    if n<1:raise ValueError("No training rows")
    m=len(train[0]["x"])
    if m!=len(FEATURE_NAMES) or any(len(row["x"])!=m for row in train):
        raise ValueError("Enriched feature dimension mismatch")
    means=[sum(r["x"][j] for r in train)/n for j in range(m)]
    std=[max(1e-5,sqrt(sum((r["x"][j]-means[j])**2 for r in train)/n)) for j in range(m)]
    w=[0.0]*m
    b=0.
    for epoch in range(epochs):
        gradient=[0.0]*m;gb=0.0
        for r in train:
            x=[max(-8,min(8,(v-means[j])/std[j])) for j,v in enumerate(r["x"])]
            p=_sigmoid(sum(w[j]*x[j] for j in range(m))+b)
            delta=p-r["y"]
            gb+=delta
            for j in range(m):gradient[j]+=delta*x[j]
        rate=0.10/(1+epoch/100)
        for j in range(m):w[j]-=rate*(gradient[j]/n+0.01*w[j])
        b-=rate*gb/n
    return {"schema":SCHEMA,"features":list(FEATURE_NAMES),
            "mean":means,"std":std,"weights":w,"bias":b,
            "execution_enabled":False}


def train_enriched(rows,raw_events,*,symbol,asset_class,seconds=60,horizon=4):
    events=normalize_events(raw_events,symbol,asset_class)
    samples,coverage=join_asof_samples(rows,events,seconds,horizon)
    train,val,test=_split(samples,horizon)
    if len(train)<80 or len(val)<20 or len(test)<20 or len({r["y"] for r in train})<2:
        return {"status":"insufficient_history","coverage":coverage,"research_only":True,
                "execution_enabled":False}
    # A model may not claim enriched training unless timely evidence is
    # represented in ALL three chronological partitions.
    represented=[sum(r["has_external_evidence"] for r in split)
                 for split in (train,val,test)]
    source_count=sum(v>0 for v in coverage["source_counts"].values())
    if (len(events)<20 or coverage["distinct_matched_events"]<20
        or min(represented)<10 or source_count<2):
        return {"status":"insufficient_external_history","coverage":coverage,
                "partition_coverage":represented,"research_only":True,
                "execution_enabled":False,
                "reason":"Need at least 20 historical timely events, two source categories and evidence in train/validation/test"}
    model=_fit_variable(train)
    validation=_evaluate(val,model,seconds=seconds)
    test_result=_evaluate(test,model,seconds=seconds)
    reasons=[]
    if test_result["samples"]<100 or test_result["signals"]<100:
        reasons.append("At least 100 held-out signals required")
    if test_result["accuracy"] is None or test_result["accuracy"]<0.60:
        reasons.append("Held-out accuracy below 60%")
    if test_result["wilson_lower_95"] is None or test_result["wilson_lower_95"]<0.50:
        reasons.append("95% confidence lower bound below 50%")
    if test_result["trades_per_hour"] is None or test_result["trades_per_hour"]<12:
        reasons.append("Historical signal frequency below 12/hour")
    if (test_result["accuracy"] is None or
        test_result["majority_baseline_accuracy"] is None or
        test_result["accuracy"]<=test_result["majority_baseline_accuracy"]):
        reasons.append("Did not beat majority baseline")
    fingerprint=sha256(json.dumps([
        [r["ts"],r["settlement_ts"],r["y"],[round(v,6) for v in r["x"]]]
        for r in samples],separators=(",",":")).encode()).hexdigest()
    return {
        "status":"validated_research_candidate" if not reasons else "candidate_not_validated",
        "research_only":True,"execution_enabled":False,
        "model":model,"dataset_fingerprint":fingerprint,
        "samples":len(samples),"train_samples":len(train),
        "validation_samples":len(val),"test_samples":len(test),
        "train_range":[train[0]["ts"],train[-1]["ts"]],
        "validation_range":[val[0]["ts"],val[-1]["ts"]],
        "test_range":[test[0]["ts"],test[-1]["ts"]],
        "horizon_bars":horizon,"seconds":seconds,
        "validation":{k:v for k,v in validation.items() if k!="decisions"},
        "test":{k:v for k,v in test_result.items() if k!="decisions"},
        "promotion_blockers":reasons,"coverage":coverage,
        "partition_coverage":represented,
        "source_categories_in_training":[k for k,v in coverage["source_counts"].items() if v>0],
        "note":"Directional historical context features from as-of-ingested research observations. This does not verify article claims or execution profitability."
    }
