"""Keep the daily search causal and its cash/stop accounting reproducible."""
import importlib.util
from pathlib import Path
import numpy as np
import pytest

root=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('daily_edge',root/'scripts/research_daily_edge.py')
research=importlib.util.module_from_spec(spec);spec.loader.exec_module(research)


def bars(n=500):
    start=research.stamp('2019-01-01')
    return [{'ts':start+i*research.DAY,'open':100+i*.1,'high':101+i*.1,'low':99+i*.1,'close':100.5+i*.1} for i in range(n)]


def plan():return {'capital_per_instrument':10000,'risk_fraction':.005,'costs':{'stocks':{'adverse_bps_each_side':1,'commission_bps_each_side':0,'carry_bps_day':0}}}


def test_monthly_and_daily_indicators_do_not_use_future_prices():
    rows=bars(800);full=research.strategy.indicators(rows);prefix=research.strategy.indicators(rows[:667])
    columns=['ema50','ema200','sma200','atr','rsi2','monthly_bias','month_decision']
    np.testing.assert_allclose(prefix[columns].astype(float),full.iloc[:667][columns].astype(float),equal_nan=True)


def test_daily_entry_is_after_signal_and_ledger_reconciles():
    rows=bars();f=research.strategy.indicators(rows);record={'symbol':'TEST','kind':'stocks','dividends':[]}
    summary,trades,_=research.replay(record,f,'sma200_trend',rows[250]['ts'],rows[-1]['ts']+research.DAY,plan())
    assert trades
    for trade in trades:
        assert trade['entry_ts']>trade['signal_ts']
        assert trade['entry_fee']>=0 and trade['exit_fee']>=0
        assert trade['units']*trade['entry']<=10000+max(0,summary['net_pnl'])+1e-6
    assert summary['net_pnl']==pytest.approx(sum(t['net_pnl'] for t in trades))


def test_daily_gap_stop_uses_observed_worse_open():
    rows=bars(270)
    for i in range(255,270):rows[i].update(open=10,high=11,low=9,close=10)
    f=research.strategy.indicators(rows);record={'symbol':'TEST','kind':'stocks','dividends':[]}
    _,trades,_=research.replay(record,f,'sma200_trend',rows[250]['ts'],rows[-1]['ts']+research.DAY,plan())
    assert trades[0]['exit_reason']=='gap_stop'
    assert trades[0]['exit']<trades[0]['stop']


def test_buy_hold_is_fully_invested_and_does_not_apply_strategy_stop():
    rows=bars(270)
    for i in range(255,270):rows[i].update(open=10,high=11,low=9,close=10)
    record={'symbol':'TEST','kind':'stocks','dividends':[]};f=research.strategy.indicators(rows)
    summary,trades,_=research.replay(record,f,'sma200_trend',rows[250]['ts'],rows[-1]['ts']+research.DAY,plan(),benchmark=True)
    assert len(trades)==1 and trades[0]['exit_reason']=='end_of_test'
    assert summary['return_pct']<-80


def test_eight_fixed_hypotheses_have_no_live_execution_path():
    assert len(research.strategy.CANDIDATES)==8
    assert 'range_fade' in research.strategy.CANDIDATES
    with pytest.raises(ValueError):research.strategy.decision(research.strategy.indicators(bars()).iloc[-1],'unknown','stocks')


def test_chandelier_stop_tightens_after_close_not_against_the_same_candle(monkeypatch):
    rows=bars(203);f=research.strategy.indicators(rows)
    f['atr']=1.;f['highest22']=110.;f['lowest22']=90.
    f.loc[200,['open','high','low','close']]=[100,101,99,100]
    f.loc[201,['open','high','low','close']]=[100,111,98,110]
    f.loc[202,['open','high','low','close']]=[110,111,108,109]
    monkeypatch.setattr(research.strategy,'decision',lambda *args:(1,False))
    costs=plan();costs['costs']['stocks']['adverse_bps_each_side']=0
    _,trades,_=research.replay({'symbol':'TEST','kind':'stocks','dividends':[]},f,'chandelier22_3atr',rows[200]['ts'],rows[-1]['ts']+research.DAY,costs)
    assert len(trades)==1 and trades[0]['entry_ts']==rows[201]['ts']
    assert trades[0]['exit_reason']=='end_of_test' and trades[0]['stop']==107
    assert trades[0]['net_pnl']>0
