"""Closed-session signals, adverse fills, dividends and missing-calendar coverage."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import research_stock_sessions as r
H=r.HOUR

def session(start=0):
    end=start+int(6.5*H)
    return [{'ts':start+i*H,'end':min(start+(i+1)*H,end),'open':100.,'high':101.,'low':99.,'close':100.,'session_start':start,'session_end':end} for i in range(7)]

def breakout():
    b=session();b[0].update(high=102.,low=99.,close=101.);b[1].update(open=101.,high=104.,low=100.,close=103.);b[2].update(open=105.,high=106.,low=104.,close=105.)
    for bar in b[3:]:bar.update(open=105.,high=106.,low=104.,close=105.)
    return b

def test_breakout_enters_next_open_instead_of_signal_close():
    rows=breakout();t=r.intraday('X','opening_range_60',rows)
    assert t['entry']==rows[2]['ts'] and t['entryPrice']==pytest.approx(105*1.0001)
    assert t['exit']<=rows[-1]['end']

def test_stop_ambiguity_and_gap_use_adverse_price():
    rows=breakout();rows[2].update(high=120.,low=98.)
    t=r.intraday('X','opening_range_60',rows);assert t['reason']=='stop' and t['exitPrice']==pytest.approx(99*.9999)
    rows=breakout();rows[3].update(open=95.,high=97.,low=94.,close=96.)
    t=r.intraday('X','opening_range_60',rows);assert t['reason']=='stop_gap' and t['exitPrice']==pytest.approx(95*.9999)

def test_target_gap_does_not_get_favorable_open():
    rows=breakout();rows[3].update(open=120.,high=121.,low=119.,close=120.)
    t=r.intraday('X','opening_range_60',rows)
    assert t['reason']=='target' and t['exitPrice']==pytest.approx(117*.9999)

def test_gap_fade_needs_prior_close_recovery_and_unfilled_target():
    rows=session();rows[0].update(open=99.,high=99.7,low=98.,close=99.5);rows[1].update(open=99.6,high=100.5,low=99.3,close=100.1)
    previous=[{'close':100.}]
    t=r.intraday('X','gap_fade_60',rows,previous)
    assert t['entry']==H and t['reason']=='target' and t['exitPrice']==pytest.approx(100*.9999)
    assert r.intraday('X','gap_fade_60',rows,None) is None
    rows[0]['open']=97.
    assert r.intraday('X','gap_fade_60',rows,previous) is None

def test_entry_delay_cannot_create_after_close_trade():
    rows=session();rows[0]['high']=102.;rows[4].update(high=104.,close=103.)
    assert r.intraday('X','opening_range_60',rows) is not None
    assert r.intraday('X','opening_range_60',rows,stress=True) is None

def test_dividend_price_drop_is_not_free_money():
    previous=session();nxt=session(24*H);nxt[0]['open']=99.;divs=[{'ts':24*H,'amount':1.}]
    t=r.overnight('ETF',previous,nxt,divs)
    assert t['dividendPerUnit']==1. and t['netBps']<0
    assert t['entry']==previous[-1]['end'] and t['exit']==nxt[0]['ts']

def test_missing_session_is_not_silently_bridged():
    a=session();b=session(24*H);record={'bars':a+b[:3]};raw={'chart':{'result':[{'meta':{'tradingPeriods':[[{'start':0,'end':int(6.5*H)//1000}],[{'start':24*H//1000,'end':int(30.5*H)//1000}]]}}]}}
    calendar,complete,meta=r.full_sessions(record,raw)
    assert len(calendar)==2 and len(complete)==1 and meta['incomplete_or_missing_sessions']==1

def test_high_win_rate_does_not_override_losing_expectancy():
    rows=[{'asset':'X','entry':i*24*H,'netBps':v} for i,v in enumerate([1.,1.,1.,-10.])]
    m=r.metrics(rows)
    assert m['profitableTradeRate']==.75 and m['meanNetBps']<0 and m['profitFactor']<1

def test_overnight_cost_stress_is_separate_from_unobserved_delay():
    a=session();b=session(24*H);b[0]['open']=101.
    base=r.overnight('X',a,b,[]);stress=r.overnight('X',a,b,[],True)
    assert stress['entry']==base['entry'] and stress['exit']==base['exit'] and stress['netBps']<base['netBps']
