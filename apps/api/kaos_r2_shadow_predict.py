"""KAOS R2 shadow forecasts using saved, *previously trained* research models.

Never place orders, authorize paper/live trading, or evaluate a future candle when
producing a forecast. All forecasts are calculated from completed, contiguous,
source-identical archived market candles. Candidate models are explicitly
UNVALIDATED, regardless of their score. These are not broker execution prices.
"""
from datetime import datetime, timezone
import math

from kaos_r2_ai_lab import FEATURES, LOOKBACK, _features, _score

MODEL_SCHEMA="kaos_r2_ohlc_logistic_v1"

def _valid_model(model):
    if not isinstance(model,dict) or model.get("schema")!=MODEL_SCHEMA:
        raise ValueError("Unsupported model schema")
    if model.get("features")!=list(FEATURES):
        raise ValueError("Model feature mismatch")
    if any(not isinstance(model.get(k),list) or len(model[k])!=len(FEATURES)
           for k in ("weights","mean","std")):
        raise ValueError("Model vector mismatch")
    values=(*model["weights"],*model["mean"],*model["std"],model.get("bias"))
    if any(not isinstance(x,(int,float)) or isinstance(x,bool) or not math.isfinite(x)
           for x in values) or any(s<=0 for s in model["std"]):
        raise ValueError("Model numerical integrity failed")

def prediction(rows, *, symbol, asset_class, seconds, source, record,
               now_ms=None, threshold=0.60):
    """Return latest closed-candle model forecast, including HOLD when uncertain.

    Latest candle must not be stale; contiguous history must have LOOKBACK+1 bars.
    Model's market, source and training schema must match current R2 market.
    """
    if not rows or seconds not in (60,300,900) or threshold<0.50 or threshold>0.90:
        raise ValueError("Invalid forecast input")
    if record.get("symbol")!=symbol or record.get("asset_class")!=asset_class:
        raise ValueError("Wrong market model")
    if record.get("source")!=source:
        raise ValueError("Model trained on another data provider")
    if record.get("seconds",60)!=seconds or record.get("horizon_bars",4)<1:
        raise ValueError("Wrong timeframe or prediction horizon")
    if record.get("status") not in ("candidate","research_active"):
        raise ValueError("Model not available for shadow research")
    if record.get("research_only") is not True or record.get("execution_enabled") is not False:
        raise ValueError("Model is not research-only")
    model=record.get("model")
    _valid_model(model)
    i=len(rows)-1
    if i<LOOKBACK:
        raise ValueError("Insufficient completed candle warmup")
    tail=rows[i-8:i+1]
    if any(b["ts"]-a["ts"]!=seconds*1000 for a,b in zip(tail,tail[1:])):
        raise ValueError("Missing candle inside model input window")
    if any(r.get("source")!=source or r.get("symbol")!=symbol or
           r.get("asset_class")!=asset_class or r.get("seconds")!=seconds
           for r in tail):
        raise ValueError("Mismatched candle provider metadata")
    if now_ms is None:
        now_ms=int(datetime.now(timezone.utc).timestamp()*1000)
    end_ms=int(tail[-1]["ts"])+seconds*1000
    if end_ms>now_ms or now_ms-end_ms>max(900000,seconds*3000):
        raise ValueError("Latest candle stale or still open")
    x=_features(rows,i)
    if not all(math.isfinite(v) for v in x):
        raise ValueError("Invalid feature values")
    prob=_score({"x":x},model)
    direction="UP" if prob>=threshold else "DOWN" if prob<=1-threshold else "HOLD"
    horizon=int(record["horizon_bars"])
    return {
        "model_id":record["id"],"model_schema":MODEL_SCHEMA,
        "validation_status":record.get("validation_status","unvalidated"),
        "research_status":record["status"],
        "symbol":symbol,"asset_class":asset_class,"seconds":seconds,
        "source":source,"observed_ts":int(tail[-1]["ts"]),
        "candle_end_ts":end_ms,
        "horizon_bars":horizon,"target_candle_ts":int(tail[-1]["ts"])+horizon*seconds*1000,
        "observed_close":float(tail[-1]["close"]),
        "prob_up":round(prob,6),"direction":direction,
        "confidence":round(max(prob,1-prob),6),
        "threshold":threshold,"outcome_status":"pending",
        "research_only":True,"execution_enabled":False,
        "broker_order_authorized":False,"paper_order_authorized":False,
        "prediction_basis":"closed_candle_research_not_executable_fill",
    }

def settle(forecast, rows):
    """Settle forecast against the future closed candle only if every intervening
    bar exists; never substitute another provider, duplicate candle or look ahead.
    If the later candle has not arrived, leave the outcome pending.
    """
    if forecast.get("outcome_status")!="pending":
        return None
    seconds=forecast["seconds"]
    start=forecast["observed_ts"]
    end=forecast["target_candle_ts"]
    if end<=start or (end-start)%(seconds*1000):
        raise ValueError("Bad forecast horizon")
    aligned={r["ts"]:r for r in rows if start<=r["ts"]<=end}
    if len(aligned)<(end-start)//(seconds*1000)+1:
        return None
    for ts in range(start,end+1,seconds*1000):
        candle=aligned[ts]
        if candle.get("source")!=forecast["source"] or candle.get("symbol")!=forecast["symbol"] or candle.get("asset_class")!=forecast["asset_class"] or candle.get("seconds")!=seconds:
            return None
    close=float(aligned[end]["close"])
    actual="UP" if close>forecast["observed_close"] else "DOWN" if close<forecast["observed_close"] else "TIE"
    side=forecast["direction"]
    return {
        "outcome_status":"settled","outcome_direction":actual,
        "settlement_ts":end,"settlement_close":close,
        "correct":None if side=="HOLD" or actual=="TIE" else side==actual,
        "return_pct":round(100*(close/float(forecast["observed_close"])-1),6),
        "fees_modeled":False,"spread_modeled":False,"slippage_modeled":False,
        "actual_trade":False,
    }
