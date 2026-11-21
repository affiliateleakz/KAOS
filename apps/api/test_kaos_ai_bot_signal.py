"""Fail-closed AI research signal preview contract tests."""
import copy
import pytest
from kaos_ai_bot_signal import signal_preview, SCHEMA

NOW=1_800_000_300_000
TS=NOW-120_000

def fixtures():
    model={"id":"r2model-1","symbol":"BTC-USD","asset_class":"crypto",
           "source":"coinbase_exchange_public","seconds":60,
           "horizon_bars":4,"status":"candidate",
           "model":{"schema":"kaos_r2_ohlc_logistic_v1"},
           "validation_status":"candidate_not_validated","promotion_blockers":["Too few test samples"],
           "research_only":True,"execution_enabled":False}
    forecast={"id":"forecast-1","model_id":"r2model-1",
              "model_schema":"kaos_r2_ohlc_logistic_v1",
              "symbol":"BTC-USD","asset_class":"crypto","source":"coinbase_exchange_public",
              "seconds":60,"horizon_bars":4,
              "observed_ts":TS-60_000,"candle_end_ts":TS,
              "target_candle_ts":TS-60_000+240_000,
              "direction":"DOWN","prob_up":0.398138,
              "outcome_status":"pending","research_only":True,"execution_enabled":False,
              "broker_order_authorized":False,"paper_order_authorized":False}
    return forecast,model

def test_unvalidated_forecast_is_visible_but_never_executable():
    forecast,model=fixtures()
    item=signal_preview(forecast,model,now_ms=NOW)
    assert item["schema"]==SCHEMA
    assert item["direction"]=="DOWN"
    assert item["bias"]=="BEARISH"
    assert item["prob_up"]==.398138
    assert "model_unvalidated" in item["block_reasons"]
    assert item["eligible_for_paper_order"] is False
    assert item["eligible_for_live_order"] is False
    assert item["suggested_order"] is None

def test_validated_model_does_not_enable_orders():
    forecast,model=fixtures()
    model.update(validation_status="validated_research_candidate",promotion_blockers=[])
    result=signal_preview(forecast,model,now_ms=NOW)
    assert result["validated_research_model"] is True
    assert result["eligible_for_paper_order"] is False
    assert result["eligible_for_live_order"] is False
    assert result["status"]=="BLOCKED"

def test_stale_and_expired_forecast_rejected_for_execution():
    forecast,model=fixtures()
    result=signal_preview(forecast,model,now_ms=NOW+500_000)
    assert "stale_forecast" in result["block_reasons"]
    assert "forecast_horizon_expired" in result["block_reasons"]

@pytest.mark.parametrize("mutate",[
    lambda f,m:f.update(broker_order_authorized=True),
    lambda f,m:f.update(execution_enabled=True),
    lambda f,m:f.update(model_id="other"),
    lambda f,m:f.update(source="wrong"),
    lambda f,m:f.update(direction="BUY"),
    lambda f,m:f.update(prob_up=float("nan")),
    lambda f,m:f.update(candle_end_ts=NOW+1),
    lambda f,m:f.update(target_candle_ts=TS+1234),
    lambda f,m:m.update(execution_enabled=True),
    lambda f,m:m.update(asset_class="stock"),
    lambda f,m:m.update(model={"schema":"made_up"}),
])
def test_mismatched_or_unsafe_inputs_fail_closed(mutate):
    forecast,model=fixtures()
    mutate(forecast,model)
    with pytest.raises(ValueError):
        signal_preview(forecast,model,now_ms=NOW)

def test_hold_is_not_a_trade_signal():
    forecast,model=fixtures()
    forecast["direction"]="HOLD"
    item=signal_preview(forecast,model,now_ms=NOW)
    assert item["bias"]=="NO_TRADE"
    assert "model_abstained" in item["block_reasons"]

def test_deterministic_id_for_same_forecast():
    forecast,model=fixtures()
    a=signal_preview(forecast,model,now_ms=NOW)
    b=signal_preview(copy.deepcopy(forecast),copy.deepcopy(model),now_ms=NOW)
    assert a["id"]==b["id"]
