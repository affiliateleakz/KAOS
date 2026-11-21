"""Deterministic KAOS AI -> Alpaca paper readiness audit.

Advisory only. Never produces an OrderIntent, paper preview, quote, or
broker request. It is deliberately impossible to interpret 'eligible'
here as authorization to transmit an order.
"""
from datetime import datetime, timezone
import math
import re

SCHEMA="kaos_ai_alpaca_paper_readiness_v1"
MODEL_SCHEMA="kaos_r2_ohlc_logistic_v1"
SUPPORTED={"stock","etf"}
SYMBOL=re.compile(r"[A-Z]{1,5}(?:[.][A-Z])?")
DIRECTION={"UP":"BUY_CANDIDATE","DOWN":"NO_SPOT_SHORT","HOLD":"ABSTAIN"}
MAX_AGE_MS=120_000
MIN_PROB=0.65


def _int(v):
    if isinstance(v,bool) or not isinstance(v,int):
        raise ValueError("Invalid time")
    return v


def review_signal(forecast,model,*,now_ms=None):
    """Audit candidate without granting broker or paper execution permission.

    All gates are independent and explicit; collecting a price quote or
    executing an order requires another, separately authorized service.
    """
    if now_ms is None:
        now_ms=int(datetime.now(timezone.utc).timestamp()*1000)
    _int(now_ms)
    if not isinstance(forecast,dict) or not isinstance(model,dict):
        raise ValueError("Model and forecast required")
    blockers=[]
    def block(reason):
        if reason not in blockers: blockers.append(reason)
    if forecast.get("research_only") is not True or forecast.get("execution_enabled") is not False:
        block("not_a_research_forecast")
    if forecast.get("broker_order_authorized") is not False or forecast.get("paper_order_authorized") is not False:
        block("forecast_execution_boundary_invalid")
    if model.get("research_only") is not True or model.get("execution_enabled") is not False:
        block("model_execution_boundary_invalid")
    if model.get("id")!=forecast.get("model_id") or not isinstance(model.get("id"),str):
        block("wrong_model_identity")
    symbol=forecast.get("symbol")
    if not isinstance(symbol,str) or not SYMBOL.fullmatch(symbol):
        block("unsupported_market_symbol")
    if forecast.get("asset_class") not in SUPPORTED or model.get("asset_class")!=forecast.get("asset_class"):
        block("asset_class_not_supported")
    if model.get("symbol")!=symbol or model.get("source")!=forecast.get("source"):
        block("model_market_or_source_mismatch")
    if forecast.get("model_schema")!=MODEL_SCHEMA or not isinstance(model.get("model"),dict) or model["model"].get("schema")!=MODEL_SCHEMA:
        block("unsupported_prediction_model")
    if model.get("validation_status")!="validated_research_candidate" or model.get("promotion_blockers"):
        block("unvalidated_model")
    if model.get("status")!="research_active":
        block("model_not_research_active")
    direction=forecast.get("direction")
    if direction not in DIRECTION:
        block("invalid_direction")
    if direction=="DOWN":
        block("spot_short_not_supported")
    elif direction=="HOLD":
        block("model_abstained")
    prob=forecast.get("prob_up")
    if isinstance(prob,bool) or not isinstance(prob,(float,int)) or not math.isfinite(prob) or not 0<=prob<=1:
        block("invalid_probability")
    elif direction=="UP" and prob<MIN_PROB:
        block("below_research_probability_threshold")
    try:
        start=_int(forecast["observed_ts"])
        end=_int(forecast["candle_end_ts"])
        target=_int(forecast["target_candle_ts"])
        seconds=_int(forecast["seconds"])
        horizon=_int(forecast["horizon_bars"])
        if seconds not in (60,300,900) or not 1<=horizon<=30:
            raise ValueError("Unsupported timeframe")
        if end>now_ms or now_ms>=target+seconds*1000:
            block("future_or_expired_forecast")
        if end!=start+seconds*1000 or target!=start+horizon*seconds*1000:
            raise ValueError("Misaligned")
        if now_ms-end>MAX_AGE_MS:
            block("stale_forecast")
    except (ValueError,TypeError,KeyError):
        block("invalid_prediction_timestamps")
    if forecast.get("outcome_status")!="pending":
        block("prediction_not_pending")
    # A separate, broker-controlled paper gateway must validate account
    # membership, current market quote, settlement, exposure and daily loss.
    # Existing KAOS stock AI models are trained on R2 archives, not on Alpaca
    # IEX quotes; matching a symbol alone cannot certify provider parity.
    block("broker_quote_unverified")
    block("alpaca_source_parity_unverified")
    block("realized_loss_and_fee_ledger_not_verified")
    block("ai_paper_execution_disabled")
    return {
        "schema":SCHEMA,
        "forecast_id":forecast.get("id"),
        "model_id":forecast.get("model_id"),
        "symbol":symbol if isinstance(symbol,str) else None,
        "direction":direction if direction in DIRECTION else None,
        "candidate_action":DIRECTION.get(direction,"NO_ACTION"),
        "prob_up":prob if isinstance(prob,(int,float)) and not isinstance(prob,bool) and math.isfinite(prob) else None,
        "reasons":blockers,
        "observational_checks_passed":not any(x in blockers for x in (
            "not_a_research_forecast","forecast_execution_boundary_invalid",
            "model_execution_boundary_invalid","wrong_model_identity",
            "unsupported_market_symbol","asset_class_not_supported",
            "model_market_or_source_mismatch","unsupported_prediction_model",
            "unvalidated_model","model_not_research_active",
            "invalid_direction","spot_short_not_supported","model_abstained",
            "invalid_probability","below_research_probability_threshold",
            "future_or_expired_forecast","stale_forecast",
            "invalid_prediction_timestamps","prediction_not_pending")),
        "paper_status":"BLOCKED",
        "paper_order_authorized":False,
        "live_order_authorized":False,
        "quantity":None,
        "order_intent":None,
        "broker_request":None,
        "research_only":True,
        "note":"Diagnostic only; this endpoint cannot create or authorize a paper broker order."
    }
