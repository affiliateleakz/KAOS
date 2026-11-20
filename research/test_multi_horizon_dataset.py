import pytest
from datetime import datetime, timezone, timedelta
from multi_horizon_dataset import make_example, DEFAULT_HORIZONS

def quotes():
    a={"symbol":"SPY","source":"equity_sip","asset_class":"stock",
       "observed_at":"2026-10-16T14:30:00Z","bid":"100.00","ask":"100.02"}
    b={**a,"observed_at":"2026-10-16T14:30:15Z","bid":"100.50","ask":"100.52"}
    return a,b

def test_supports_short_and_long_horizons():
    a,b=quotes()
    assert 15 in DEFAULT_HORIZONS and 604800 in DEFAULT_HORIZONS
    assert make_example(a,b,15)["buy_profitable"]

def test_sell_profit_when_price_falls():
    a,b=quotes()
    b.update(bid="99.40",ask="99.42")
    outcome=make_example(a,b,15)
    assert outcome["sell_profitable"] and not outcome["buy_profitable"]

def test_wide_spread_can_make_both_unprofitable():
    a,b=quotes()
    b.update(bid="99.99",ask="100.03")
    assert make_example(a,b,15)["no_trade_preferred"]

def test_future_news_not_in_features():
    a,b=quotes()
    events=[
      {"event_id":"one","kind":"filing","source":"sec","published_at":"2026-10-16T14:00:00Z","received_at":"2026-10-16T14:29:00Z"},
      {"event_id":"two","kind":"news","source":"news","published_at":"2026-10-16T14:00:00Z","received_at":"2026-10-16T14:30:01Z"},
      {"event_id":"three","kind":"short_interest","source":"finra","published_at":"2026-10-16T15:00:00Z","received_at":"2026-10-16T15:00:01Z"},
    ]
    out=make_example(a,b,15,events)
    assert [x["event_id"] for x in out["available_events"]]==["one"]

def test_no_cross_source_or_symbol():
    a,b=quotes()
    b["source"]="different_feed"
    with pytest.raises(ValueError,match="different instruments"):make_example(a,b,15)

def test_no_missing_expiration_data_or_lookahead():
    a,b=quotes()
    b["observed_at"]="2026-10-16T14:31:00Z"
    with pytest.raises(ValueError,match="exact expiry"):make_example(a,b,15)

def test_simulated_prices_not_eligible():
    a,b=quotes()
    a["simulated"]=True
    with pytest.raises(ValueError,match="Untrusted"):make_example(a,b,15)

def test_frictions_change_profitability():
    a,b=quotes()
    b.update(bid="100.03",ask="100.05")
    assert make_example(a,b,15,fee_bps=10)["no_trade_preferred"]
