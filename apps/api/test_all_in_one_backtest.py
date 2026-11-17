"""Protect All-in-one chronology, stop fills, cash ledger and FX conversion."""
import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

root=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('all_in_one_replay',root/'scripts/backtest_all_in_one.py')
replay=importlib.util.module_from_spec(spec);spec.loader.exec_module(replay)
strategy=replay.strategy
START=1735689600000


def bars(n=3):
    return [{'ts':START+i*3600000,'end':START+(i+1)*3600000,'open':100.,'high':100.2,'low':99.5,'close':100.,'session_start':None,'session_end':None} for i in range(n)]


def plan():return {'capital_per_instrument':10000,'risk_fraction':.0025,'costs':{'stocks':{'adverse_bps_each_side':0,'commission_bps_each_side':0,'carry_bps_day':0}}}


def run(rows,stop=99,dividends=None):
    candidates={0:{'side':1,'stop':stop,'signal_close':100,'signal_ts':START+3600000,'atr':2}}
    return replay.backtest({'symbol':'TEST','kind':'stocks','dividends':dividends or []},pd.DataFrame(rows),candidates,START+3600000,START+len(rows)*3600000,plan())


def test_next_open_entry_and_stop_first_on_ambiguous_bar():
    rows=bars();rows[1].update(high=103,low=98)
    summary,trades,_=run(rows)
    assert trades[0]['entry_ts']==START+3600000
    assert trades[0]['target']==102 and trades[0]['stop']==99
    assert trades[0]['exit_reason']=='stop_first_ambiguous'
    assert trades[0]['net_R']==-1 and summary['ending_equity']==9975


def test_gap_stop_fills_at_worse_open_not_the_stop_price():
    rows=bars();rows[2].update(open=98,high=98.2,low=97,close=98)
    summary,trades,_=run(rows)
    assert trades[0]['exit_reason']=='gap_stop' and trades[0]['exit']==98
    assert trades[0]['net_R']==-2 and summary['ending_equity']==9950


def test_entry_gap_filter_cancels_stale_price():
    rows=bars();rows[1].update(open=102,high=102,low=101,close=102)
    summary,trades,_=run(rows)
    assert trades==[] and summary['counts']['gap_entries_cancelled']==1


def test_whole_share_notional_cannot_exceed_capital():
    summary,trades,_=run(bars(),stop=99.9999)
    assert trades[0]['units']<=100
    assert trades[0]['units']*trades[0]['entry']<=10000
    assert summary['ending_equity']==10000+sum(t['net_pnl'] for t in trades)


def test_cash_dividend_offsets_ex_date_price_drop_without_double_counting():
    rows=bars();rows[2].update(open=99.5,high=99.7,low=99.4,close=99.5)
    summary,trades,_=run(rows,dividends=[{'ts':rows[2]['ts'],'amount':.5}])
    assert trades[0]['dividends']==12.5
    assert trades[0]['gross_price_pnl']==-12.5
    assert summary['ending_equity']==10000 and trades[0]['net_pnl']==0


def test_usdjpy_profit_is_converted_at_exit_price():
    assert replay.usd_pnl('USDJPY=X',100,150,149,-1)==pytest.approx(100/149)
    assert replay.notional('USDJPY=X',100,150)==100
    assert replay.usd_pnl('EURUSD=X',100,1.1,1.2,1)==pytest.approx(10)


def test_forex_carry_uses_calendar_time():
    position={'units':100,'entry':150,'entry_ts':START}
    assert replay.carry('USDJPY=X',position,START+3*replay.DAY,{'carry_bps_day':2})==pytest.approx(.06)


def test_higher_timeframe_and_entry_features_do_not_look_ahead():
    rows=bars(1200)
    for i,row in enumerate(rows):
        price=100+i*.01+np.sin(i/9);row.update(open=price,high=price+.2,low=price-.2,close=price+.05)
    full,_=strategy.indicators(rows,'crypto');prefix,_=strategy.indicators(rows[:1101],'crypto')
    np.testing.assert_allclose(prefix[['bias','ema20','ema50','atr']],full.iloc[:1101][['bias','ema20','ema50','atr']],equal_nan=True)


def test_stock_four_hour_groups_complete_at_actual_session_close():
    start=START+14*3600000+1800000;end=start+int(6.5*3600000)
    rows=[{**b,'ts':start+i*3600000,'end':min(start+(i+1)*3600000,end),'session_start':start,'session_end':end} for i,b in enumerate(bars(7))]
    _,quality=strategy.indicators(rows,'stocks')
    assert quality['complete_four_hour_bars']==2 and quality['incomplete_four_hour_groups_excluded']==0


def test_reclaim_confirmation_uses_known_prior_high_and_pullback_low():
    f=pd.DataFrame([{'open':100,'high':100.3,'low':99.2,'close':99.5},{'open':100,'high':101,'low':99.8,'close':100.8}])
    f['bias']=1;f['ema20']=100;f['ema50']=99;f['atr']=2;f['quote_gap']=False;f['end']=[START+3600000,START+7200000]
    signals=strategy.signals(f,'stocks')
    assert list(signals)==[1] and signals[1]['stop']==pytest.approx(98.7)
    f['bias']=-1
    assert strategy.signals(f,'stocks')=={} and strategy.signals(f,'crypto')=={}


def test_unscheduled_quote_gap_cancels_preceding_pending_entry():
    rows=bars();rows[1]['quote_gap']=True
    summary,trades,_=run(rows)
    assert not trades and summary['counts']['gap_entries_cancelled']==1
