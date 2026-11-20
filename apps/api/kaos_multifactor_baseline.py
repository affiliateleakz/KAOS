"""KAOS original multi-factor logistic research baseline, fully offline.

Uses completed single-source candles plus time-eligible evidence. Strict
chronological train/validation/test split, no orders or production inference.
No claim that output scores are calibrated probabilities.
"""
from math import exp, isfinite, log, sqrt
from kaos_market_assessment import ema, rsi, atr
from kaos_point_in_time import available_evidence

FEATURES=(
    "ema20_distance","ema20_vs_ema50","rsi14_centered",
    "macd_fraction","atr_fraction","volume_ratio_minus_one",
    "return_5","return_20","news_vote","social_vote",
    "filing_vote","options_flow_vote","other_vote",
    "news_observed","social_observed","filing_observed","options_flow_observed",
)

def sigmoid(x):
    z=max(-35.0,min(35.0,x))
    return 1.0/(1.0+exp(-z))

def _features(history, observations, *, symbol, asset_class, cutoff_ms):
    close=[float(r["close"]) for r in history[-100:]]
    if len(close)<60 or min(close)<=0:return None
    last=close[-1]
    e20=ema(close,20)
    e50=ema(close,50)
    macd=ema(close,12)-ema(close,26)
    volatility=atr(history[-30:]) or 0.0
    volume=[r.get("volume") for r in history[-21:]]
    if len(volume)!=21 or any(type(v) not in (int,float) or not isfinite(v) or v<0 for v in volume):
        ratio=0.
    else:
        previous=sum(volume[:-1])/20
        ratio=volume[-1]/previous-1 if previous else 0.
    indicators=[
        last/e20-1,e20/e50-1,((rsi(close) or 50)-50)/50,
        macd/last,volatility/last,max(-5.,min(5.,ratio)),
        last/close[-6]-1,last/close[-21]-1,
    ]
    evidence,_=available_evidence(observations,as_of_ms=cutoff_ms,
                    symbol=symbol,asset_class=asset_class)
    bucket={"news":[],"social":[],"filing":[],"options_flow":[],"other":[]}
    for item in evidence:
        name=item["source"] if item["source"] in bucket else "other"
        val=item["strength"]*(1 if item["direction"]=="bullish" else
                              -1 if item["direction"]=="bearish" else 0)
        bucket[name].append(val)
    votes=[sum(vals)/len(vals) if vals else 0. for vals in bucket.values()]
    flags=[1. if bucket[name] else 0. for name in ("news","social","filing","options_flow")]
    result=indicators+votes+flags
    if len(result)!=len(FEATURES) or not all(isfinite(x) for x in result):
        return None
    return result

def dataset(candles, observations, *, symbol,asset_class,seconds,source,
            horizon=5,lookback=80):
    if type(horizon) is not int or not 1<=horizon<=30:
        raise ValueError("Unsupported label horizon")
    if not isinstance(candles,list) or len(candles)>10000:
        raise ValueError("Invalid historical archive")
    if not isinstance(observations,list) or len(observations)>5000:
        raise ValueError("Invalid intelligence archive")
    rows=sorted(candles,key=lambda r:r["ts"])
    interval=seconds*1000
    seen=set()
    for r in rows:
        stamp=r.get("ts")
        if (type(stamp) is not int or stamp in seen or stamp<=0 or
            r.get("symbol")!=symbol or r.get("asset_class")!=asset_class or
            r.get("seconds")!=seconds or r.get("source")!=source):
            raise ValueError("Invalid or mixed historical candle identity")
        seen.add(stamp)
        try: vals=[float(r[k]) for k in ("open","high","low","close")]
        except (KeyError,ValueError,TypeError) as exc:raise ValueError("Missing OHLC") from exc
        if (not all(isfinite(v) and v>0 for v in vals) or
            vals[1]<max(vals[0],vals[3]) or vals[2]>min(vals[0],vals[3])):
            raise ValueError("Inconsistent OHLC")
    samples=[]
    # Disjoint evaluation windows and a bounded lookback. Never read an
    # outcome candle in model inputs for the decision immediately preceding it.
    for i in range(max(lookback,60)-1,len(rows)-horizon,horizon+1):
        segment=rows[i-max(lookback,60)+1:i+horizon+1]
        if any(b["ts"]-a["ts"]!=interval for a,b in zip(segment,segment[1:])):
            continue
        cutoff=rows[i]["ts"]+interval
        x=_features(rows[:i+1],observations,symbol=symbol,
                    asset_class=asset_class,cutoff_ms=cutoff)
        if x is None:continue
        entry=rows[i+1]["open"]
        ret=rows[i+horizon]["close"]/entry-1
        samples.append({"decision_ms":cutoff,
            "label_end_ms":rows[i+horizon]["ts"]+interval,
            "x":x,"up":1 if ret>0 else 0,"forward_return":ret})
    return samples

def split(rows,minimum=20):
    if len(rows)<minimum*5:
        return None
    a=int(len(rows)*.6);b=int(len(rows)*.8)
    val_cut=rows[a]["decision_ms"]
    test_cut=rows[b]["decision_ms"]
    train=[r for r in rows[:a] if r["label_end_ms"]<=val_cut]
    validation=[r for r in rows[a:b] if r["label_end_ms"]<=test_cut]
    test=rows[b:]
    if min(len(train),len(validation),len(test))<minimum:
        return None
    return train,validation,test

def train_logistic(rows, epochs=350,lr=.12,l2=.015):
    """Train only on train partition, with train-only standardization."""
    n=len(FEATURES)
    means=[sum(r["x"][j] for r in rows)/len(rows) for j in range(n)]
    scales=[max(sqrt(sum((r["x"][j]-means[j])**2 for r in rows)/len(rows)),1e-6)
            for j in range(n)]
    xs=[[(r["x"][j]-means[j])/scales[j] for j in range(n)] for r in rows]
    w=[0.]*n
    base=sum(r["up"] for r in rows)/len(rows)
    bias=log(max(.01,min(.99,base))/max(.01,1-min(.99,base)))
    for _ in range(epochs):
        gw=[l2*x for x in w];gb=0.
        for features,r in zip(xs,rows):
            diff=sigmoid(bias+sum(a*b for a,b in zip(w,features)))-r["up"]
            gb+=diff
            for j,val in enumerate(features):gw[j]+=diff*val/len(rows)
        bias-=lr*gb/len(rows)
        w=[a-lr*g for a,g in zip(w,gw)]
    return {"weights":w,"bias":bias,"means":means,"scales":scales}

def predict(model,x):
    z=model["bias"]+sum(w*(v-m)/s for w,v,m,s in zip(
        model["weights"],x,model["means"],model["scales"]))
    return sigmoid(z)

def metrics(model,partition,*,cost_bps,threshold=.55):
    scored=[]
    for row in partition:
        p=predict(model,row["x"])
        side=1 if p>=threshold else -1 if p<=1-threshold else 0
        scored.append({"p":p,"label":row["up"],"side":side,"return":row["forward_return"]})
    signals=[r for r in scored if r["side"]]
    cost=cost_bps/10000
    net=[r["side"]*r["return"]-cost for r in signals]
    return {
        "samples":len(scored),"signals":len(signals),
        "abstentions":len(scored)-len(signals),
        "accuracy_all":round(sum((r["p"]>=.5)==bool(r["label"]) for r in scored)/len(scored),5),
        "brier_score":round(sum((r["p"]-r["label"])**2 for r in scored)/len(scored),6),
        "mean_proxy_after_cost":round(sum(net)/len(net),8) if net else None,
        "positive_net_fraction":round(sum(v>0 for v in net)/len(net),5) if net else None,
    }

def evaluate(candles,observations,*,symbol,asset_class,seconds,source,
             horizon=5,cost_bps=10.,min_split=20):
    if (type(cost_bps) not in (int,float) or not isfinite(cost_bps) or
            not 0<=cost_bps<=250):
        raise ValueError("Invalid cost")
    rows=dataset(candles,observations,symbol=symbol,asset_class=asset_class,
                 seconds=seconds,source=source,horizon=horizon)
    parts=split(rows,min_split)
    if parts is None:
        return {"status":"insufficient_point_in_time_training_data",
                "samples":len(rows),"research_only":True,"model_trained":False,
                "options_validated":False}
    train,val,test=parts
    model=train_logistic(train)
    # Validation is assessed before the untouched test but does not control
    # model tuning; fixed 0.55 abstention threshold across partitions.
    validation=metrics(model,val,cost_bps=cost_bps)
    holdout=metrics(model,test,cost_bps=cost_bps)
    majority=1 if sum(r["up"] for r in train)*2>=len(train) else 0
    base_acc=sum(r["up"]==majority for r in test)/len(test)
    base_brier=sum((majority-r["up"])**2 for r in test)/len(test)
    base_return=sum((1 if majority else -1)*r["forward_return"]-
                    cost_bps/10000 for r in test)/len(test)
    return {
        "status":"unvalidated_multifactor_baseline","model":"offline_logistic_v1",
        "feature_names":list(FEATURES),"market":symbol,"asset_class":asset_class,
        "source":source,"seconds":seconds,"horizon":horizon,
        "train_samples":len(train),"validation_samples":len(val),
        "test_samples":len(test),
        "train_last_outcome_ms":train[-1]["label_end_ms"],
        "validation_first_decision_ms":val[0]["decision_ms"],
        "validation_last_outcome_ms":val[-1]["label_end_ms"],
        "test_first_decision_ms":test[0]["decision_ms"],
        "validation":validation,"holdout":holdout,
        "holdout_majority_accuracy":round(base_acc,5),
        "holdout_majority_brier_score":round(base_brier,6),
        "holdout_majority_mean_cost_adjusted_proxy":round(base_return,8),
        "cost_bps_assumed":cost_bps,
        "scores_calibrated":False,"model_deployed":False,
        "options_validated":False,"orders_enabled":False,"research_only":True,
        "warnings":[
            "Toy statistical baseline is NOT trained Kronos/CNN or a validated trading predictor",
            "Missing evidence is encoded separately; historical archive coverage may be incomplete",
            "Probabilities are raw uncalibrated logistic scores and not reliable trade probabilities",
            "Price-return proxies omit realistic option contract execution and fill risks",
        ],
    }
