"""Deterministic R2 candle learning lab; pure Python, no live-trading authority.

Feature vectors use completed-bar OHLC only, label the direction at a future
completed-bar CLOSE. Chronological train/validation/test splits have purged
horizon boundaries. Research model is independent from KAOS live AI registry.
"""
import hashlib
import json
import math

FEATURES = ("ret1", "ret3", "ret8", "range", "body", "upper_wick", "lower_wick", "volume_change")
LOOKBACK = 9

def _sigmoid(x):
    return 1 / (1 + math.exp(-max(-30, min(30, x))))

def _wilson_lower(correct, total, z=1.96):
    if not total:
        return 0.0
    p = correct/total
    a = z*z
    return max(0.0, ((p + a/(2*total)) - z*math.sqrt(p*(1-p)/total+a/(4*total*total)))/(1+a/total))

def _features(rows, i):
    r = rows[i]
    c = float(r["close"])
    o = float(r["open"])
    h = float(r["high"])
    l = float(r["low"])
    base = max(c, 1e-12)
    vol = float(r.get("volume") or 0)
    prev_vol = float(rows[i-1].get("volume") or 0)
    return [
        (c/float(rows[i-1]["close"])-1)*100,
        (c/float(rows[i-3]["close"])-1)*100,
        (c/float(rows[i-8]["close"])-1)*100,
        (h-l)/base*100,
        (c-o)/base*100,
        (h-max(o,c))/base*100,
        (min(o,c)-l)/base*100,
        max(-3.0,min(3.0,(vol-prev_vol)/max(1.0,prev_vol))),
    ]

def make_samples(rows, seconds=60, horizon=4):
    if seconds not in (60,300,900) or not isinstance(horizon,int) or isinstance(horizon,bool) or not 1<=horizon<=30:
        raise ValueError("Invalid timeframe or horizon")
    if not isinstance(rows,list):
        raise ValueError("Expected candle list")
    interval = seconds*1000
    out = []
    for i in range(LOOKBACK,len(rows)-horizon):
        # Every feature and settlement candle must belong to the same contiguous block.
        window = rows[i-8:i+horizon+1]
        if any(b["ts"]-a["ts"]!=interval for a,b in zip(window,window[1:])):
            continue
        future = float(rows[i+horizon]["close"])
        current = float(rows[i]["close"])
        if current <= 0 or future <= 0 or current == future:
            continue
        x = _features(rows,i)
        if not all(math.isfinite(v) for v in x):
            continue
        out.append({"ts":int(rows[i]["ts"]),"settlement_ts":int(rows[i+horizon]["ts"]),
                    "x":x,"y":int(future>current)})
    return out

def _split(samples, horizon):
    # Segregate by chronological timestamps, then purge overlapping label horizons.
    n = len(samples)
    a=int(n*0.60); b=int(n*0.80)
    train=samples[:a]
    validation=samples[a:b]
    test=samples[b:]
    if validation:
        train=[r for r in train if r["settlement_ts"]<validation[0]["ts"]]
    if test:
        validation=[r for r in validation if r["settlement_ts"]<test[0]["ts"]]
    return train,validation,test

def _fit(train, epochs=200):
    m=len(FEATURES)
    means=[sum(r["x"][j] for r in train)/len(train) for j in range(m)]
    stds=[max(1e-5,math.sqrt(sum((r["x"][j]-means[j])**2 for r in train)/len(train))) for j in range(m)]
    w=[0.0]*m
    b=0.0
    # Fixed-order batch gradient descent, no randomness or external API.
    for epoch in range(epochs):
        grad=[0.0]*m; gb=0.0
        for r in train:
            x=[max(-8,min(8,(v-means[j])/stds[j])) for j,v in enumerate(r["x"])]
            p=_sigmoid(sum(w[j]*x[j] for j in range(m))+b)
            err=p-r["y"]
            gb+=err
            for j in range(m):
                grad[j]+=err*x[j]
        rate=0.12/(1+epoch/100)
        for j in range(m):
            w[j]-=rate*(grad[j]/len(train)+0.01*w[j])
        b-=rate*gb/len(train)
    return {"features":list(FEATURES),"mean":means,"std":stds,
            "weights":w,"bias":b,"schema":"kaos_r2_ohlc_logistic_v1"}

def _score(sample, model):
    v=sum(model["weights"][j]*max(-8,min(8,(x-model["mean"][j])/model["std"][j]))
          for j,x in enumerate(sample["x"]))+model["bias"]
    return _sigmoid(v)

def _evaluate(rows, model, *, seconds, threshold=0.60):
    decisions=[]
    for r in rows:
        p=_score(r,model)
        side=1 if p>=threshold else 0 if p<=1-threshold else None
        if side is None:
            continue
        decisions.append({"ts":r["ts"],"settlement_ts":r["settlement_ts"],"prediction":"UP" if side else "DOWN",
                          "prob_up":round(p,5),"correct":bool(side==r["y"])})
    wins=sum(d["correct"] for d in decisions)
    n=len(decisions)
    duration_hours=((rows[-1]["ts"]-rows[0]["ts"])/3600000) if len(rows)>1 else 0
    majority=max(sum(r["y"] for r in rows),sum(1-r["y"] for r in rows))/len(rows) if rows else None
    return {"samples":len(rows),"signals":n,"correct":wins,"incorrect":n-wins,
            "accuracy":round(wins/n,4) if n else None,
            "wilson_lower_95":round(_wilson_lower(wins,n),4) if n else None,
            "trades_per_hour":round(n/duration_hours,2) if duration_hours else None,
            "majority_baseline_accuracy":round(majority,4) if majority is not None else None,
            "decisions":decisions}

def train_from_candles(rows, seconds=60, horizon=4):
    samples=make_samples(rows,seconds,horizon)
    train,val,test=_split(samples,horizon)
    if len(train)<80 or len(val)<20 or len(test)<20 or len({r["y"] for r in train})<2:
        return {"status":"insufficient_training_history",
                "samples":len(samples),"train_samples":len(train),
                "validation_samples":len(val),"test_samples":len(test),
                "required":"at least 80 training, 20 validation, 20 unseen test samples, both classes",
                "research_only":True,"execution_enabled":False}
    model=_fit(train)
    validation=_evaluate(val,model,seconds=seconds)
    test_metrics=_evaluate(test,model,seconds=seconds)
    # Performance requirements apply to untouched chronological test ONLY.
    # Deliberately require far more than a 300-candle snapshot to promote.
    reasons=[]
    if test_metrics["samples"]<100 or test_metrics["signals"]<100:
        reasons.append("At least 100 untouched test samples and 100 triggered predictions required")
    if test_metrics["accuracy"] is None or test_metrics["accuracy"]<0.60:
        reasons.append("Test accuracy below 60%")
    if test_metrics["wilson_lower_95"] is None or test_metrics["wilson_lower_95"]<0.50:
        reasons.append("95% Wilson lower bound below 50%")
    if test_metrics["trades_per_hour"] is None or test_metrics["trades_per_hour"]<12:
        reasons.append("Test signals per observed hour below 12")
    if test_metrics["accuracy"] is None or test_metrics["majority_baseline_accuracy"] is None or test_metrics["accuracy"]<=test_metrics["majority_baseline_accuracy"]:
        reasons.append("Not better than majority baseline")
    digest=hashlib.sha256(json.dumps(
        [[r["ts"],r["settlement_ts"],r["y"]] for r in samples],
        separators=(",",":")).encode()).hexdigest()
    return {"status":"validated_research_candidate" if not reasons else "candidate_not_validated",
            "research_only":True,"execution_enabled":False,
            "model":model,"dataset_fingerprint":digest,
            "samples":len(samples),"train_samples":len(train),
            "validation_samples":len(val),"test_samples":len(test),
            "train_range":[train[0]["ts"],train[-1]["ts"]],
            "validation_range":[val[0]["ts"],val[-1]["ts"]],
            "test_range":[test[0]["ts"],test[-1]["ts"]],
            "horizon_bars":horizon,"seconds":seconds,
            "validation":{k:v for k,v in validation.items() if k!="decisions"},
            "test":{k:v for k,v in test_metrics.items() if k!="decisions"},
            "promotion_blockers":reasons,
            "test_predictions":test_metrics["decisions"][-100:]}
