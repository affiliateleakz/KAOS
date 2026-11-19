"""Unverified/stale/ambiguous research cannot become executable orders."""
from datetime import datetime, timezone, timedelta
from kaos_opportunity_fusion import evaluate_opportunity

NOW = datetime(2026,10,19,tzinfo=timezone.utc)

def entry(source, direction="BUY", **kwargs):
    return {"source": source, "asset": "SPY", "direction": direction, "timestamp": NOW,
            "verified": True, "simulated": False, **kwargs}

def test_fresh_strategy_and_chart_produce_research_candidate_only():
    out = evaluate_opportunity("SPY","alpaca",[entry("strategy"),entry("chart"),
                    entry("news",direction="SELL")],now=NOW)
    assert out["candidate_direction"] == "BUY"
    assert out["context_conflicts"] == ["news"]
    assert out["executable"] is False

def test_news_and_social_alone_cannot_trigger_trade():
    out = evaluate_opportunity("SPY","alpaca",[entry("news"),entry("social"),
                    entry("financial_llm")],now=NOW)
    assert out["status"] == "NO_TRADE"
    assert out["executable"] is False

def test_stale_unverified_and_conflicting_market_sources_fail_closed():
    rows=[entry("strategy"),entry("chart",direction="SELL"),
          entry("indicators",timestamp=NOW-timedelta(hours=2)),
          entry("orderflow",verified=False)]
    out=evaluate_opportunity("SPY","alpaca",rows,now=NOW)
    assert out["candidate_direction"] is None
    assert len(out["excluded_evidence"]) == 2

def test_strategy_cannot_self_confirm_without_market_data():
    out=evaluate_opportunity("SPY","alpaca",[entry("strategy"),entry("news")],now=NOW)
    assert out["status"] == "NO_TRADE"
    assert out["candidate_direction"] is None
    assert out["executable"] is False

def test_unverified_chart_does_not_confirm_strategy():
    out=evaluate_opportunity("SPY","alpaca",[
        entry("strategy"),entry("chart",verified=False)],now=NOW)
    assert out["candidate_direction"] is None
