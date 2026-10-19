from market_feature_join import make_market_example

def test_join_includes_known_news_and_closed_chart_features():
    entry={"symbol":"SPY","source":"alpaca","asset_class":"stock",
           "observed_at":"1970-01-01T00:03:00Z","bid":"10","ask":"10.01"}
    exit_quote={**entry,"observed_at":"1970-01-01T00:03:15Z","bid":"10.20","ask":"10.21"}
    candles=[{"symbol":"SPY","source":"alpaca","seconds":60,"ts":t*1000,
              "open":10,"high":h,"low":9,"close":c}
             for t,h,c in ((0,11,10),(60,11,10),(120,14,13))]
    events=[{"asset":"SPY","source":"news","event_id":"old",
             "published_at":"1970-01-01T00:01:00Z","first_received_at":"1970-01-01T00:02:00Z"},
            {"asset":"SPY","source":"news","event_id":"late",
             "published_at":"1970-01-01T00:01:00Z","first_received_at":"1970-01-01T00:04:00Z"}]
    result=make_market_example(entry,exit_quote,15,events,candles,periods=(60,))
    assert result["chart_features"]["60"]["breakout_high"]
    assert [e["event_id"] for e in result["available_events"]]==["old"]
    assert result["buy_profitable"]
