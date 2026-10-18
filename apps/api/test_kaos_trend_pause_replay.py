import pytest
from kaos_trend_pause_replay import replay

def candle(ts,p):
    return {"ts":ts,"open":p,"high":p+0.1,"low":p-0.1,"close":p}

def test_empty_and_no_fabricated_trades():
    assert replay([],[])["summary"]["trades"] == 0
    minute=[candle(i*60000,100) for i in range(75)]
    fast=[candle(i*15000,100) for i in range(300)]
    result=replay(minute,fast)
    assert result["trades"] == []
    assert result["summary"]["win_rate_ex_ties"] is None
    assert result["summary"]["profitable"] is None

def test_horizon_validation():
    with pytest.raises(ValueError):
        replay([],[],horizon_seconds=7)
    with pytest.raises(ValueError):
        replay([],[],horizon_seconds=0)

def test_no_future_bar_no_marked_trade(monkeypatch):
    import kaos_trend_pause_replay as engine
    monkeypatch.setattr(engine,"signal",lambda a,b: {"direction":"CALL","pause_candles":1})
    minute=[candle(i*60000,100) for i in range(100)]
    fast=[candle(i*15000,100) for i in range(20)]
    result=replay(minute,fast,horizon_seconds=60)
    assert all(t["exit_ts"] in {c["ts"] for c in fast} for t in result["trades"])
    assert all(t["research_only"] for t in result["trades"])
    assert all(t["exit_ts"]-t["entry_ts"]==60000 for t in result["trades"])
