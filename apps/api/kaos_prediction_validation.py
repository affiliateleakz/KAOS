"""KAOS chronological forward-outcome evaluation on archived closed candles.

Read-only research. No downloaded candles, network calls, AI model fitting,
orders, option P&L claims or fabricated empirical performance.
"""
import math
from datetime import datetime, timezone
from kaos_market_assessment import assess
from kaos_point_in_time import available_evidence, fixed_fusion

def evaluate_history(candles, *, symbol, asset_class, seconds, source,
                     horizon=5, fee_bps=10.0, min_history=80, min_test=20,
                     observations=None):
    """Evaluate fixed technical research decisions with a future-held-out period.

    Each decision receives ONLY candles available through its decision close.
    Entry proxy: next bar OPEN. Exit proxy: horizon-th bar CLOSE. No positions
    overlap. Time split is chronological; a purge prevents label crossing.
    Baseline: majority next-bar-to-horizon direction from the training period,
    fixed once before evaluating the holdout.
    """
    if observations is not None and (not isinstance(observations,list) or len(observations)>5000):
        raise ValueError("Bounded intelligence observations required")
    if type(horizon) is not int or not 1<=horizon<=60:
        raise ValueError("Invalid horizon")
    if type(seconds) is not int or seconds<=0:
        raise ValueError("Invalid timeframe")
    if type(fee_bps) not in (int,float) or not math.isfinite(fee_bps) or not 0<=fee_bps<=250:
        raise ValueError("Invalid assumed cost")
    if not isinstance(candles,list) or len(candles)>100000:
        raise ValueError("Invalid or unbounded archive")
    ordered=sorted(candles,key=lambda r:r["ts"])
    for row in ordered:
        if (row.get("symbol")!=symbol or row.get("asset_class")!=asset_class or
                row.get("seconds")!=seconds or row.get("source")!=source):
            raise ValueError("Mixed market or provenance")
        if type(row.get("ts")) is not int:
            raise ValueError("Missing timestamp")
        fields=[row.get(k) for k in ("open","high","low","close")]
        if any(type(v) not in (int,float) or not math.isfinite(v) for v in fields):
            raise ValueError("Invalid OHLC")
        o,hi,lo,cl=fields
        if min(fields)<=0 or lo>min(o,cl) or hi<max(o,cl):
            raise ValueError("Inconsistent OHLC")
    if len({r["ts"] for r in ordered})!=len(ordered):
        raise ValueError("Duplicate timestamp")
    min_history=max(55,min_history)
    if len(ordered)<min_history+min_test*2*(horizon+1):
        return {"status":"insufficient_archived_history","decision_count":0,
                "reason":"Not enough archived closed candles for a purged train/test evaluation",
                "research_only":True,"options_validated":False}
    # Never use an unfinished bar; historical corpus is assumed to consist of
    # closed bars whose timestamps are their bar-open UTC instants.
    data=[]
    for i in range(min_history-1,len(ordered)-horizon,horizon+1):
        # Require all lookback and future evaluation bars to be contiguous
        # before evaluating an entry, so no overnight gaps are fabricated.
        window=ordered[i-min_history+1:i+horizon+1]
        if any(b["ts"]-a["ts"]!=seconds*1000 for a,b in zip(window,window[1:])):
            continue
        history=ordered[:i+1]
        decision_ms=ordered[i]["ts"]+seconds*1000
        result=assess(history,[],symbol=symbol,asset_class=asset_class,
                      seconds=seconds,source=source,now_ms=decision_ms)
        direction=result.get("buy_sell")
        eligible=[]
        if observations is not None:
            eligible,_=available_evidence(observations,as_of_ms=decision_ms,
                                           symbol=symbol,asset_class=asset_class)
        joint=fixed_fusion(result,eligible) if observations is not None else "WAIT"
        if direction not in ("RESEARCH_BULLISH","RESEARCH_BEARISH","WAIT"):
            continue
        entry=ordered[i+1]["open"]
        exit_close=ordered[i+horizon]["close"]
        simple_return=exit_close/entry-1
        data.append({"decision_ms":decision_ms,
                     "outcome_ms":ordered[i+horizon]["ts"]+seconds*1000,
                     "direction":direction,"joint_direction":joint,
                     "eligible_sources":len({o["source"] for o in eligible}),
                     "forward_return":simple_return})
    # Classify the first 70% as calibration and hold out the final 30%.
    if len(data)<min_test*3:
        return {"status":"insufficient_valid_decisions","decision_count":len(data),
                "reason":"Too few contiguous, nonoverlapping historical decisions",
                "research_only":True,"options_validated":False}
    cut=int(len(data)*.7)
    held_start=data[cut]["decision_ms"]
    training=[r for r in data[:cut] if r["outcome_ms"]<=held_start]
    test=data[cut:]
    if len(training)<min_test or len(test)<min_test:
        return {"status":"insufficient_valid_decisions","decision_count":len(data),
                "research_only":True,"options_validated":False}
    # A constant baseline direction chosen solely on training outcomes.
    up=sum(r["forward_return"]>0 for r in training)
    down=sum(r["forward_return"]<0 for r in training)
    baseline_direction=1 if up>=down else -1
    cost=fee_bps/10000.0
    scored=[]
    fusion_scored=[]
    for r in test:
        side=1 if r["direction"]=="RESEARCH_BULLISH" else -1 if r["direction"]=="RESEARCH_BEARISH" else 0
        if not side:continue
        net=side*r["forward_return"]-cost
        baseline=baseline_direction*r["forward_return"]-cost
        scored.append({"decision_ms":r["decision_ms"],"outcome_ms":r["outcome_ms"],
                       "direction":r["direction"],"net_return_proxy":net,
                       "baseline_net_return_proxy":baseline})
        if observations is not None and r["joint_direction"]==r["direction"]:
            fusion_scored.append({"net_return_proxy":net,
                                  "technical_net_return_proxy":net,
                                  "baseline_net_return_proxy":baseline})
    if len(scored)<min_test:
        return {"status":"insufficient_holdout_signals","decision_count":len(data),
                "holdout_signals":len(scored),"holdout_waits":len(test)-len(scored),
                "research_only":True,"options_validated":False}
    fusion_summary=None
    if observations is not None:
        # Compare all policies on the SAME filtered decision dates. This
        # avoids overstating a selective filter against a different sample.
        fusion_summary={
            "status":"matched_holdout_research" if len(fusion_scored)>=min_test
                     else "insufficient_matched_fusion_signals",
            "holdout_fusion_signals":len(fusion_scored),
            "holdout_technical_signals":len(scored),
            "holdout_fusion_waits":len(test)-len(fusion_scored),
            "rule":"technical_signal_plus_two_independent_agreeing_evidence_categories",
            "no_calibrated_probability":True,
            "mean_fusion_return_proxy":round(sum(x["net_return_proxy"] for x in fusion_scored)/len(fusion_scored),8) if len(fusion_scored)>=min_test else None,
            "mean_baseline_proxy_on_fusion_dates":round(sum(x["baseline_net_return_proxy"] for x in fusion_scored)/len(fusion_scored),8) if len(fusion_scored)>=min_test else None,
            "note":"Fixed rule; no trained weights; only already-ingested evidence usable at each historical cutoff. Historical evidence coverage can be sparse."
        }
    return {
        "status":"unvalidated_historical_research",
        "symbol":symbol,"asset_class":asset_class,"source":source,
        "seconds":seconds,"horizon_bars":horizon,"cost_bps_assumed":fee_bps,
        "decision_count":len(data),
        "train_decisions":len(training),"holdout_decisions":len(test),
        "holdout_signals":len(scored),"holdout_waits":len(test)-len(scored),
        "train_last_outcome_ms":training[-1]["outcome_ms"],
        "holdout_first_decision_ms":test[0]["decision_ms"],
        "holdout_start_ms":test[0]["decision_ms"],
        "holdout_end_ms":test[-1]["outcome_ms"],
        "majority_baseline_direction":"UP" if baseline_direction>0 else "DOWN",
        "directional_win_fraction_after_costs":round(
            sum(x["net_return_proxy"]>0 for x in scored)/len(scored),5),
        "baseline_win_fraction_on_same_signals":round(
            sum(x["baseline_net_return_proxy"]>0 for x in scored)/len(scored),5),
        "mean_net_return_proxy":round(
            sum(x["net_return_proxy"] for x in scored)/len(scored),8),
        "baseline_mean_net_return_proxy":round(
            sum(x["baseline_net_return_proxy"] for x in scored)/len(scored),8),
        "point_in_time_fusion":fusion_summary,
        "entries_at":"next_candle_open","exits_at":"horizon_candle_close",
        "research_only":True,"orders_enabled":False,"options_validated":False,
        "notice":"Chronological held-out price-direction proxy; not option P&L or executable backtest. Gaps excluded; costs assumed; no model training or calibrated prediction.",
    }
