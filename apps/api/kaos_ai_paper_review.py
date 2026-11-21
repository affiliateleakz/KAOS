"""Read-only KAOS AI versus Alpaca paper-order research comparison.

This deliberately does not create trading signals, attribute manual trades to AI,
infer profitable execution, or authorize paper/live orders. Only historical
research forecasts available before an independent manual paper order are shown.
"""
from datetime import datetime,timezone
import math

MAX_FORECAST_AGE_SECONDS = 300
SUPPORTED_CLASSES = {"stock","etf"}
BROKER_TERMINAL = {"filled", "canceled", "expired", "rejected", "done_for_day"}


def _utc(value):
    if isinstance(value,datetime):
        result=value
    elif isinstance(value,str):
        result=datetime.fromisoformat(value.replace("Z","+00:00"))
    else:
        raise ValueError("Missing timestamp")
    if result.tzinfo is None:
        raise ValueError("Timezone-unaware timestamp")
    return result.astimezone(timezone.utc)


def _order_time_ms(order):
    return int(_utc(order["created_at"]).timestamp()*1000)


def _forecast_ok(forecast,order_time_ms,symbol):
    if not isinstance(forecast,dict):
        return False
    if forecast.get("symbol")!=symbol or forecast.get("asset_class") not in SUPPORTED_CLASSES:
        return False
    if forecast.get("research_only") is not True or forecast.get("execution_enabled") is not False:
        return False
    if forecast.get("broker_order_authorized") is not False or forecast.get("paper_order_authorized") is not False:
        return False
    if forecast.get("direction") not in ("UP","DOWN","HOLD"):
        return False
    try:
        candle_end=int(forecast["candle_end_ts"])
        target=int(forecast["target_candle_ts"])
        observed=int(forecast["observed_ts"])
        p=float(forecast["prob_up"])
    except (ValueError,KeyError,TypeError,OverflowError):
        return False
    if isinstance(forecast.get("candle_end_ts"),bool) or not math.isfinite(p) or not 0<=p<=1:
        return False
    # The recorded research model can only be consulted after its candle
    # closed, before the horizon expired, and while it is reasonably recent.
    return (observed<candle_end<=order_time_ms<target
            and order_time_ms-candle_end<=MAX_FORECAST_AGE_SECONDS*1000)


def review_manual_paper_orders(orders,forecasts,owned_model_ids):
    """Compare matching historical forecasts without asserting trade causality."""
    if not isinstance(orders,list) or not isinstance(forecasts,list):
        raise ValueError("Invalid input")
    owned=set(owned_model_ids)
    results=[]
    matched=0
    filled=0
    for order in orders[:50]:
        if not isinstance(order,dict) or order.get("broker")!="alpaca_paper" or order.get("ai_order") is not False:
            continue
        symbol=order.get("symbol")
        if not isinstance(symbol,str) or not symbol or len(symbol)>16:
            continue
        try:
            t=_order_time_ms(order)
        except (ValueError,KeyError,TypeError,OverflowError):
            continue
        candidates=[f for f in forecasts
            if f.get("model_id") in owned and _forecast_ok(f,t,symbol)]
        candidates.sort(key=lambda f:f["candle_end_ts"],reverse=True)
        forecast=candidates[0] if candidates else None
        status=order.get("broker_status")
        if status=="filled":filled+=1
        if forecast:matched+=1
        output={
            "client_order_id":order.get("client_order_id"),
            "symbol":symbol,
            "manual_paper_order":True,
            "created_at":order["created_at"],
            "broker_status":status or order.get("state"),
            "broker_filled_qty":order.get("filled_qty"),
            "broker_filled_avg_price":order.get("filled_avg_price"),
            "research_forecast_matched":bool(forecast),
            "ai_caused_order":False,
            "profitability_verified":False,
            "trade_realized_pnl":None,
            "execution_authorized":False,
        }
        if forecast:
            output["research_forecast"]={
                "forecast_id":forecast.get("id"),"model_id":forecast.get("model_id"),
                "bias":forecast["direction"],
                "prob_up":forecast["prob_up"],
                "candle_end_ts":forecast["candle_end_ts"],
                "target_candle_ts":forecast["target_candle_ts"],
                "outcome_status":forecast.get("outcome_status"),
                "outcome_direction":forecast.get("outcome_direction"),
                "correct":forecast.get("correct") if forecast.get("outcome_status")=="settled" else None,
                "available_before_manual_order":True,
            }
        results.append(output)
    return {
        "schema":"kaos_alpaca_paper_ai_review_v1",
        "orders_reviewed":len(results),
        "matched_prior_research_forecasts":matched,
        "broker_reported_filled_orders":filled,
        "rows":results,
        "research_only":True,"order_submission_enabled":False,
        "ai_execution_enabled":False,
        "accuracy_is_not_pnl":True,
        "note":"Manual paper orders were never caused or authorized by these AI forecasts. "
               "Directional outcomes are independent of actual Alpaca fills, fees, and realized P&L."
    }
