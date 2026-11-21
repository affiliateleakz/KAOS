"""AI-to-paper eligibility must never open Alpaca execution authority."""
from datetime import datetime,timezone
import pytest
from kaos_ai_alpaca_readiness import review_signal,SCHEMA

NOW=1_800_000_300_000

def fixtures():
    model={"id":"candidate-stock-1","symbol":"AAPL","asset_class":"stock",
        "source":"alpaca_iex","model":{"schema":"kaos_r2_ohlc_logistic_v1"},
        "validation_status":"validated_research_candidate","promotion_blockers":[],
        "status":"research_active","research_only":True,"execution_enabled":False}
    forecast={"id":"forecast-1","model_id":"candidate-stock-1",
        "symbol":"AAPL","asset_class":"stock","source":"alpaca_iex",
        "direction":"UP","prob_up":.72,"model_schema":"kaos_r2_ohlc_logistic_v1",
        "seconds":60,"horizon_bars":4,"observed_ts":NOW-120000,
        "candle_end_ts":NOW-60000,"target_candle_ts":NOW+120000,
        "outcome_status":"pending","research_only":True,"execution_enabled":False,
        "broker_order_authorized":False,"paper_order_authorized":False}
    return forecast,model

def test_even_qualified_candidate_is_never_executable():
    f,m=fixtures()
    row=review_signal(f,m,now_ms=NOW)
    assert row["schema"]==SCHEMA
    assert row["observational_checks_passed"] is True
    assert row["paper_status"]=="BLOCKED"
    assert row["paper_order_authorized"] is False
    assert row["live_order_authorized"] is False
    assert row["broker_request"] is None
    assert row["order_intent"] is None
    assert row["quantity"] is None
    assert "alpaca_source_parity_unverified" in row["reasons"]
    assert "realized_loss_and_fee_ledger_not_verified" in row["reasons"]

@pytest.mark.parametrize("edit,reason",[
    ({"direction":"HOLD"},"model_abstained"),
    ({"direction":"DOWN","prob_up":.2},"spot_short_not_supported"),
    ({"direction":"UP","prob_up":.5},"below_research_probability_threshold"),
    ({"candle_end_ts":NOW+1000},"future_or_expired_forecast"),
    ({"model_id":"wrong"},"wrong_model_identity"),
    ({"execution_enabled":True},"not_a_research_forecast"),
    ({"paper_order_authorized":True},"forecast_execution_boundary_invalid"),
    ({"asset_class":"option"},"asset_class_not_supported"),
])
def test_bad_forecast_remains_blocked(edit,reason):
    f,m=fixtures()
    f.update(edit)
    row=review_signal(f,m,now_ms=NOW)
    assert reason in row["reasons"]
    assert row["observational_checks_passed"] is False
    assert row["paper_order_authorized"] is False

def test_unvalidated_model_not_promoted_by_probability():
    f,m=fixtures()
    f["prob_up"]=0.99
    m["validation_status"]="candidate_not_validated"
    row=review_signal(f,m,now_ms=NOW)
    assert "unvalidated_model" in row["reasons"]
    assert row["paper_order_authorized"] is False

def test_stale_and_settled_prediction_cannot_be_treated_as_current():
    f,m=fixtures()
    f.update(observed_ts=NOW-420000,candle_end_ts=NOW-360000,
             target_candle_ts=NOW-180000,outcome_status="settled")
    row=review_signal(f,m,now_ms=NOW)
    assert "stale_forecast" in row["reasons"]
    assert "prediction_not_pending" in row["reasons"]
    assert row["paper_status"]=="BLOCKED"

def test_nan_and_boolean_probability_rejected_without_throwing():
    f,m=fixtures()
    for p in (float("nan"),True,float("inf")):
        f["prob_up"]=p
        row=review_signal(f,m,now_ms=NOW)
        assert "invalid_probability" in row["reasons"]
        assert row["prob_up"] is None
