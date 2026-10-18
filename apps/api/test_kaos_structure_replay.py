import pytest
from kaos_structure_replay import replay

def bar(i,p=100):
    return {"ts":i*15000,"open":p,"high":p+1,"low":p-1,"close":p}

def test_flat_series_has_no_fabricated_trades():
    result=replay([bar(i) for i in range(100)])
    assert result["trades"]==[]
    assert result["summary"]["win_rate_ex_ties"] is None

def test_gapped_history_is_rejected():
    rows=[bar(i) for i in range(50)]
    rows[25]["ts"]+=1
    with pytest.raises(ValueError,match="uniform candle"):
        replay(rows)

def test_expiry_is_bounded():
    with pytest.raises(ValueError):
        replay([],expiry_bars=0)

def test_marked_trades_do_not_overlap(monkeypatch):
    import kaos_structure_replay as engine
    monkeypatch.setattr(engine,"signal",lambda bars,lookback:{"direction":"CALL","setup":"BREAKOUT","level":100})
    rows=[bar(i,100+i*.01) for i in range(70)]
    result=replay(rows,expiry_bars=4)
    trades=result["trades"]
    assert trades
    assert all(t["exit_ts"]-t["entry_ts"]==60000 for t in trades)
    assert all(a["exit_ts"]<b["entry_ts"] for a,b in zip(trades,trades[1:]))
    assert result["summary"]["trades"]==len(trades)
