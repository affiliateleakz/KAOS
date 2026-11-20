"""KAOS research prediction model lifecycle: fit, register, approve, infer.

Owner builds candidate from archived, point-in-time data. Only independently
approved candidate artifacts can serve member research forecasts. Predictions
never give an order authority, guaranteed win probability, or option contract.
"""
from hashlib import sha256
import json
from math import isfinite
from kaos_multifactor_baseline import (
    dataset, split, train_logistic, predict, _features, metrics, evidence_coverage,
    TECHNICAL_INDICES, ALL_INDICES,
)

MIN_TRAIN=100
MIN_VALIDATION=25
MIN_TEST=25
MIN_TEST_ACCURACY=0.51
MIN_IMPROVEMENT=0.01


def build_candidate(candles,observations,*,symbol,asset_class,seconds,source,
                    horizon=5,cost_bps=10.0):
    """Build a bounded, unapproved candidate artifact from actual archives."""
    samples=dataset(candles,observations,symbol=symbol,asset_class=asset_class,
                    seconds=seconds,source=source,horizon=horizon)
    partitions=split(samples,minimum=MIN_TEST)
    if partitions is None:
        return {"status":"insufficient_data","candidate":None,
                "reason":"Not enough clean nonoverlapping historical decisions",
                "sample_count":len(samples)}
    train,validation,test=partitions
    if len(train)<MIN_TRAIN or len(validation)<MIN_VALIDATION or len(test)<MIN_TEST:
        return {"status":"insufficient_data","candidate":None,
                "reason":"Train, validation or held-out sample count below minimum",
                "sample_count":len(samples)}
    train_cov=evidence_coverage(train)
    test_cov=evidence_coverage(test)
    # Never pretend the 'all source' model learned external evidence when
    # original first-seen observations were not available at training time.
    use_multi=(train_cov["samples_with_observed_evidence"]>=MIN_VALIDATION
               and test_cov["samples_with_observed_evidence"]>=MIN_VALIDATION)
    selected=ALL_INDICES if use_multi else TECHNICAL_INDICES
    candidate_model=train_logistic(train,feature_indices=selected)
    val=metrics(candidate_model,validation,cost_bps=cost_bps)
    hold=metrics(candidate_model,test,cost_bps=cost_bps)
    technical=train_logistic(train,feature_indices=TECHNICAL_INDICES)
    tech_hold=metrics(technical,test,cost_bps=cost_bps)
    base_up=sum(r["up"] for r in train)/len(train)
    # Training-prevalence constant baseline, evaluated without test fitting.
    base_brier=sum((base_up-r["up"])**2 for r in test)/len(test)
    base_acc=sum((base_up>=.5)==bool(r["up"]) for r in test)/len(test)
    # A conservative eligibility screen for further human review, not proof
    # of statistical significance or a verified trading edge.
    quality_pass=(hold["accuracy_all"]>=max(MIN_TEST_ACCURACY,base_acc+MIN_IMPROVEMENT)
                  and hold["brier_score"]<base_brier
                  and hold["signals"]>=MIN_TEST)
    latest=max(c["ts"] for c in candles)
    artifact={
        "schema":"kaos_research_logistic_v1","symbol":symbol,
        "asset_class":asset_class,"seconds":seconds,"source":source,
        "horizon_bars":horizon,"last_training_candle_ms":latest,
        "selected_features":"multifactor" if use_multi else "technical_only",
        "model":candidate_model,
        "training_examples":len(train),"validation_examples":len(validation),
        "holdout_examples":len(test),
        "first_test_decision_ms":test[0]["decision_ms"],
        "train_last_outcome_ms":train[-1]["label_end_ms"],
        "validation_last_outcome_ms":validation[-1]["label_end_ms"],
        "validation_metrics":val,"holdout_metrics":hold,
        "technical_only_holdout":tech_hold,
        "baseline_brier":round(base_brier,6),
        "baseline_accuracy":round(base_acc,5),
        "train_intelligence_coverage":train_cov,
        "test_intelligence_coverage":test_cov,
        "quality_screen_pass":quality_pass,
        "orders_enabled":False,"scores_calibrated":False,
        "research_only":True,
    }
    payload=json.dumps(artifact,sort_keys=True,separators=(",",":"),allow_nan=False)
    artifact["model_digest"]=sha256(payload.encode("utf-8")).hexdigest()
    return {"status":"candidate_ready_for_review" if quality_pass else
            "candidate_rejected_by_quality_screen",
            "candidate":artifact,
            "reason":"Requires independent owner review and explicit approval; held-out screen is not a reliable live profit guarantee"}


def infer_candidate(artifact,candles,observations,*,now_ms):
    """Generate fresh research direction from a reviewed artifact only."""
    if not artifact or artifact.get("schema")!="kaos_research_logistic_v1":
        return {"status":"no_approved_model","direction":"WAIT"}
    if not artifact.get("approved") or not artifact.get("quality_screen_pass"):
        return {"status":"model_not_approved","direction":"WAIT"}
    required=("symbol","asset_class","seconds","source")
    if not isinstance(candles,list) or not 100<=len(candles)<=5000:
        return {"status":"insufficient_live_history","direction":"WAIT"}
    rows=sorted(candles,key=lambda r:r["ts"])
    recent=rows[-100:]
    if any(r.get(k)!=artifact[k] for r in recent for k in required):
        return {"status":"source_or_market_mismatch","direction":"WAIT"}
    interval=artifact["seconds"]*1000
    if any(b["ts"]-a["ts"]!=interval for a,b in zip(recent,recent[1:])):
        return {"status":"recent_candle_gaps","direction":"WAIT"}
    cutoff=recent[-1]["ts"]+interval
    if cutoff>now_ms or now_ms-cutoff>max(3*interval,5*60000):
        return {"status":"stale_or_incomplete_candles","direction":"WAIT"}
    if recent[-1]["ts"]<=artifact["last_training_candle_ms"]:
        return {"status":"model_not_forward_of_training","direction":"WAIT"}
    try:
        x=_features(recent,observations,symbol=artifact["symbol"],
                    asset_class=artifact["asset_class"],cutoff_ms=cutoff)
        if x is None:return {"status":"invalid_features","direction":"WAIT"}
        raw=predict(artifact["model"],x)
    except (KeyError,IndexError,TypeError,ValueError,ZeroDivisionError,OverflowError):
        return {"status":"invalid_model_or_features","direction":"WAIT"}
    if not isfinite(raw):return {"status":"invalid_model_output","direction":"WAIT"}
    direction="BULLISH" if raw>=.55 else "BEARISH" if raw<=.45 else "WAIT"
    return {
        "status":"experimental_prediction" if direction!="WAIT" else "experimental_abstention",
        "symbol":artifact["symbol"],"asset_class":artifact["asset_class"],
        "timeframe_seconds":artifact["seconds"],"horizon_bars":artifact["horizon_bars"],
        "horizon_seconds":artifact["seconds"]*artifact["horizon_bars"],
        "last_closed_candle_ms":cutoff,"direction":direction,
        "raw_model_up_score":round(raw,5),
        "score_type":"uncalibrated_model_output_not_a_win_probability",
        "source":artifact["source"],"model_digest":artifact["model_digest"],
        "model_family":artifact["selected_features"],
        "research_only":True,"orders_enabled":False,
        "options":{"call_put":"NONE","contract":None,"expiration":None},
        "note":"Experimental directional forecast. Not a calibrated probability, order, or options recommendation."
    }
