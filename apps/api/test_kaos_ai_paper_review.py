"""Read-only forecast/manual Alpaca paper order matching tests."""
from datetime import datetime,timezone,timedelta

from kaos_ai_paper_review import review_manual_paper_orders

AT=datetime(2026,11,20,19,0,tzinfo=timezone.utc)
MS=int(AT.timestamp()*1000)
ORDER={
    "client_order_id":"kaos-paper-abc","broker":"alpaca_paper",
    "symbol":"AAPL","ai_order":False,"created_at":AT.isoformat(),
    "state":"BROKER_REPORTED","broker_status":"filled",
    "filled_qty":"0.2","filled_avg_price":"100",
}
FORECAST={
    "id":"f1","model_id":"owner-model","symbol":"AAPL",
    "asset_class":"stock","direction":"UP","prob_up":0.68,
    "observed_ts":MS-180000,"candle_end_ts":MS-120000,
    "target_candle_ts":MS+120000,
    "research_only":True,"execution_enabled":False,
    "broker_order_authorized":False,"paper_order_authorized":False,
    "outcome_status":"pending",
}

def test_prior_owner_forecast_can_be_reviewed_without_ai_trade_claim():
    result=review_manual_paper_orders([ORDER],[FORECAST],["owner-model"])
    row=result["rows"][0]
    assert row["research_forecast"]["bias"]=="UP"
    assert row["research_forecast"]["correct"] is None
    assert row["ai_caused_order"] is False
    assert row["profitability_verified"] is False
    assert row["trade_realized_pnl"] is None
    assert result["broker_reported_filled_orders"]==1
    assert result["matched_prior_research_forecasts"]==1
    assert result["ai_execution_enabled"] is False

def test_future_and_stale_research_cannot_match():
    future={**FORECAST,"candle_end_ts":MS+1000}
    stale={**FORECAST,"candle_end_ts":MS-360000,"observed_ts":MS-420000}
    report=review_manual_paper_orders([ORDER],[future,stale],["owner-model"])
    assert report["matched_prior_research_forecasts"]==0

def test_foreign_model_or_unauthorized_forecast_cannot_match():
    report=review_manual_paper_orders([ORDER],[FORECAST],["another-model"])
    assert report["matched_prior_research_forecasts"]==0
    tainted={**FORECAST,"paper_order_authorized":True}
    assert review_manual_paper_orders([ORDER],[tainted],["owner-model"])["matched_prior_research_forecasts"]==0

def test_ai_triggered_record_never_represented_as_manual():
    order={**ORDER,"ai_order":True}
    result=review_manual_paper_orders([order],[FORECAST],["owner-model"])
    assert result["orders_reviewed"]==0

def test_expired_horizon_not_matched():
    expired={**FORECAST,"target_candle_ts":MS-1000}
    assert review_manual_paper_orders([ORDER],[expired],["owner-model"])["matched_prior_research_forecasts"]==0

def test_latest_eligible_forecast_wins():
    older={**FORECAST,"id":"old","observed_ts":MS-240000,"candle_end_ts":MS-180000}
    result=review_manual_paper_orders([ORDER],[older,FORECAST],["owner-model"])
    assert result["rows"][0]["research_forecast"]["forecast_id"]=="f1"

def test_no_unsupported_asset_class_matches():
    option={**FORECAST,"asset_class":"option"}
    assert review_manual_paper_orders([ORDER],[option],["owner-model"])["matched_prior_research_forecasts"]==0
