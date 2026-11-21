"""Versioned read-only KAOS AI -> Bot research signal contract.

This module describes completed-candle model forecasts for bot *observation*.
It does NOT grant paper or live order authority. In particular it cannot
represent a binary CALL/PUT as an executable stock/crypto BUY/SELL.
"""
from datetime import datetime, timezone
import hashlib
import math

SCHEMA="kaos_ai_bot_signal_preview_v1"
MODEL_SCHEMA="kaos_r2_ohlc_logistic_v1"
SUPPORTED_ASSETS={"stock","etf","crypto","forex"}
SIDE={"UP":"BULLISH","DOWN":"BEARISH","HOLD":"NO_TRADE"}
MAX_STALENESS_MS=300_000

def signal_preview(forecast, model, *, now_ms=None):
    if not isinstance(forecast,dict) or not isinstance(model,dict):
        raise ValueError("Forecast and research model required")
    if now_ms is None:
        now_ms=int(datetime.now(timezone.utc).timestamp()*1000)
    if not isinstance(now_ms,int) or isinstance(now_ms,bool):
        raise ValueError("Invalid clock")
    keys=("id","model_id","symbol","asset_class","source","seconds","horizon_bars",
          "observed_ts","candle_end_ts","target_candle_ts","direction","prob_up")
    if any(key not in forecast for key in keys):
        raise ValueError("Incomplete forecast")
    if not isinstance(forecast["id"],str) or not forecast["id"]:
        raise ValueError("Missing forecast ID")
    if forecast["asset_class"] not in SUPPORTED_ASSETS:
        raise ValueError("Options and binary payouts need specialized models")
    if forecast["direction"] not in SIDE:
        raise ValueError("Invalid prediction direction")
    if forecast["model_id"]!=model.get("id"):
        raise ValueError("Forecast model identity mismatch")
    if forecast["symbol"]!=model.get("symbol") or forecast["asset_class"]!=model.get("asset_class"):
        raise ValueError("Model market mismatch")
    if forecast["source"]!=model.get("source"):
        raise ValueError("Model data source mismatch")
    if model.get("model",{}).get("schema")!=MODEL_SCHEMA:
        raise ValueError("Unsupported model schema")
    if forecast.get("model_schema")!=MODEL_SCHEMA:
        raise ValueError("Unsupported forecast schema")
    if forecast["seconds"]!=model.get("seconds",60) or forecast["horizon_bars"]!=model.get("horizon_bars"):
        raise ValueError("Horizon mismatch")
    if forecast.get("research_only") is not True or forecast.get("execution_enabled") is not False:
        raise ValueError("Forecast not research-only")
    if model.get("research_only") is not True or model.get("execution_enabled") is not False:
        raise ValueError("Model not research-only")
    if forecast.get("broker_order_authorized") is not False or forecast.get("paper_order_authorized") is not False:
        raise ValueError("Forecast did not explicitly deny order authority")
    if not isinstance(forecast["seconds"],int) or isinstance(forecast["seconds"],bool) or forecast["seconds"] not in (60,300,900):
        raise ValueError("Unsupported candle timeframe")
    if not isinstance(forecast["horizon_bars"],int) or isinstance(forecast["horizon_bars"],bool) or not 1<=forecast["horizon_bars"]<=30:
        raise ValueError("Unsupported forecast horizon")
    if any(not isinstance(forecast[key],int) or isinstance(forecast[key],bool)
           for key in ("observed_ts","candle_end_ts","target_candle_ts")):
        raise ValueError("Invalid candle timestamps")
    interval=forecast["seconds"]*1000
    if forecast["candle_end_ts"]!=forecast["observed_ts"]+interval or forecast["target_candle_ts"]!=forecast["observed_ts"]+forecast["horizon_bars"]*interval:
        raise ValueError("Misaligned forecast timestamps")
    if forecast["candle_end_ts"]>now_ms:
        raise ValueError("Forecast candle has not closed")
    probability=forecast["prob_up"]
    if not isinstance(probability,(int,float)) or isinstance(probability,bool) or not math.isfinite(probability) or not 0<=probability<=1:
        raise ValueError("Invalid model probability")
    if forecast.get("outcome_status") not in ("pending","settled"):
        raise ValueError("Unknown forecast settlement state")
    if model.get("status") not in ("candidate","research_active"):
        raise ValueError("Unavailable research model")
    validated=(model.get("validation_status")=="validated_research_candidate"
               and not model.get("promotion_blockers"))
    stale=now_ms-forecast["candle_end_ts"]>MAX_STALENESS_MS
    expired=now_ms>=forecast["target_candle_ts"]+interval
    signal_id="kaos-r2-"+hashlib.sha256(
        f'{forecast["id"]}|{model["id"]}|{SCHEMA}'.encode()).hexdigest()[:32]
    reasons=[]
    if forecast["direction"]=="HOLD":
        reasons.append("model_abstained")
    if not validated:
        reasons.append("model_unvalidated")
    if stale:
        reasons.append("stale_forecast")
    if expired:
        reasons.append("forecast_horizon_expired")
    # This feed is a *preview*. Even a validated model does not authorize
    # execution without separate entitlement, real quote and risk checks.
    reasons.append("research_preview_no_execution_authority")
    return {
        "schema":SCHEMA,"id":signal_id,"forecast_id":forecast["id"],
        "model_id":model["id"],"model_schema":MODEL_SCHEMA,
        "symbol":forecast["symbol"],"asset_class":forecast["asset_class"],
        "source":forecast["source"],
        "timeframe_seconds":forecast["seconds"],
        "horizon_seconds":forecast["seconds"]*forecast["horizon_bars"],
        "direction":forecast["direction"],"bias":SIDE[forecast["direction"]],
        "prob_up":round(float(probability),6),
        "observed_ts":forecast["observed_ts"],
        "closed_at_ms":forecast["candle_end_ts"],
        "target_candle_ts":forecast["target_candle_ts"],
        "outcome_status":forecast["outcome_status"],
        "data_status":"stale" if stale else "recent",
        "model_validation_status":model.get("validation_status","unknown"),
        "validated_research_model":bool(validated),
        "status":"BLOCKED" if reasons else "OBSERVATION",
        "block_reasons":reasons,
        "suggested_order":None,"broker":None,"quantity":None,
        "broker_quote_verified":False,
        "eligible_for_paper_order":False,"eligible_for_live_order":False,
        "execution_enabled":False,"research_only":True,
        "note":"AI research observation only. Never route this preview to an order endpoint."
    }
