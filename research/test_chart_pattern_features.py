from chart_pattern_features import features_at

def row(t, o, h, l, c, **overrides):
    x={"symbol":"SPY","source":"alpaca","seconds":60,"ts":t*1000,
       "open":o,"high":h,"low":l,"close":c}
    x.update(overrides)
    return x

def test_breakout_and_closed_candle_only():
    rows=[row(0,10,11,9,10),row(60,10,11,9,10),row(120,10,14,10,13)]
    result=features_at(rows, "1970-01-01T00:03:00Z",symbol="SPY",source="alpaca",periods=(60,))
    assert result["60"]["breakout_high"]
    before=features_at(rows, "1970-01-01T00:02:59Z",symbol="SPY",source="alpaca",periods=(60,))
    assert "60" not in before

def test_future_and_cross_market_bars_excluded():
    rows=[row(0,10,11,9,10),row(60,10,11,9,10),row(120,10,11,9,10),
          row(180,10,100,9,99),row(120,10,100,9,99,symbol="QQQ"),
          row(120,10,100,9,99,source="unrelated")]
    result=features_at(rows,"1970-01-01T00:03:00Z",symbol="SPY",source="alpaca",periods=(60,))
    assert not result["60"]["breakout_high"]

def test_duplicates_do_not_change_count():
    rows=[row(0,10,11,9,10),row(60,10,11,9,10),row(120,10,11,9,10)]
    outcome=features_at(rows+rows,"1970-01-01T00:03:00Z",
                        symbol="SPY",source="alpaca",periods=(60,))
    assert outcome["60"]["bars"]==3

def test_simulated_candles_never_used():
    rows=[row(0,10,11,9,10),row(60,10,11,9,10),
          row(120,10,50,9,40,simulated=True)]
    assert features_at(rows,"1970-01-01T00:03:00Z",
                       symbol="SPY",source="alpaca",periods=(60,))=={}
