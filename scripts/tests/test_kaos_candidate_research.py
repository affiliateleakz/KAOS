"""Causal calculations, conservative fills, and paper-only boundaries."""
import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
PATH=Path(__file__).resolve().parents[2]/'research/kaos_candidate_v1/strategy.py'
spec=importlib.util.spec_from_file_location('candidate',PATH);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def bars(n=300,tf=60):
    c=100+np.arange(n)*.01
    return np.column_stack((np.arange(n)*tf*1000,c,c+1,c-1,c+.1))

def test_features_prefix_and_wilder_seed():
    a=bars();before=m.features(a[:260]);a[260:,1:]+=50;after=m.features(a)
    for col in ['ema20','ema50','ema200','atr','prior_high','prior_low']:
        np.testing.assert_allclose(before[col],after[col].iloc[:260],equal_nan=True)
    assert before.atr.iloc[13]==pytest.approx(2)

def test_stop_first_and_gap_through_stop():
    a=bars(10);a[2,2]=110;a[2,3]=90
    assert m.spot_exit(a,2,5,98,105)==(2,98.,'stop')
    a[2,1]=95
    assert m.spot_exit(a,2,5,98,105)==(2,95.,'stop')

def test_target_limit_and_timeout():
    a=bars(10);a[2,1]=110;a[2,2]=111;a[2,3]=109
    assert m.spot_exit(a,2,5,98,105)==(2,105.,'target')
    a=bars(10)
    assert m.spot_exit(a,2,5,90,120)==(5,a[5,1],'time')

def test_no_split_crossing_and_stress_costs():
    a=bars(150);f=pd.DataFrame({'ts':[0],'atr':[1.]});sig=np.array([True])
    assert m.spot_replay('BTCUSDT',a,f,sig,300,1.5,(0,3600000))==[]
    b=m.spot_replay('BTCUSDT',a,f,sig,300,1.5,(0,99999999))[0]
    s=m.spot_replay('BTCUSDT',a,f,sig,300,1.5,(0,99999999),True)[0]
    assert s['entry']==b['entry']+60000
    assert s['netR']<b['netR']
    assert not s['executionEnabled']

def test_no_overlapping_or_same_exit_minute_entries():
    a=bars(250);f=pd.DataFrame({'ts':np.arange(40)*300000,'atr':np.ones(40)})
    rows=m.spot_replay('BTCUSDT',a,f,np.ones(40,dtype=bool),300,1.5,(0,99999999))
    assert len(rows)>=2
    for first,second in zip(rows,rows[1:]):assert second['entry']>first['exit']

def test_binary_combined_delay_and_adverse_fill():
    a=bars(100,5);a[:,1:]=100
    f=pd.DataFrame({'ts':[0]});sig=np.array([1])
    b=m.binary_replay('PO',a,f,sig,60,60,(0,999999))[0]
    s=m.binary_replay('PO',a,f,sig,60,60,(0,999999),True)[0]
    assert b['outcome']==0 and s['outcome']==-1
    assert s['entry']==b['entry']+5000
    assert s['exit']-s['entry']==60000

def test_paper_guardrails():
    a=bars(300,300);closed=a[-1,0]+300000
    assert m.paper_signal(a,as_of_ms=closed)['reason']=='unsupported_market'
    for now in [closed-1,closed+60001]:
        r=m.paper_signal(a,as_of_ms=now,symbol='BTCUSDT')
        assert r['action']=='HOLD' and r['executionEnabled'] is False
    a[-2,0]+=1000
    with pytest.raises(ValueError):m.paper_signal(a,as_of_ms=closed,symbol='BTCUSDT')


def test_positive_raw_performance_cannot_override_failed_stress_or_benchmark():
    import sys
    sys.path.insert(0,str(PATH.parents[2]/'scripts'))
    import research_kaos_candidates as runner
    b={'trades':200,'days':30,'profit_factor':1.2,'net':20.,'lower_day_bootstrap_mean':.1,'asset_net':{'a':5,'b':5,'c':5,'d':5},'mean_per_trade':.1}
    bench={'always_long':{'mean_per_trade':.05},'trend_long':{'mean_per_trade':.02}}
    assert runner.spot_gate(b,{'net':1},bench)
    assert not runner.spot_gate(b,{'net':-1},bench)
    assert not runner.spot_gate(b,{'net':1},{'stronger':{'mean_per_trade':.2}})
    assert not runner.spot_gate({**b,'lower_day_bootstrap_mean':-.1},{'net':1},bench)


def test_binary_historical_gate_requires_adverse_fill_survival():
    import sys
    sys.path.insert(0,str(PATH.parents[2]/'scripts'))
    import research_kaos_candidates as runner
    rows=[{'asset':'a' if i%2 else 'b','entry':(i%4)*86400000+i*5000,'outcome':1 if i<140 else -1} for i in range(200)]
    b=runner.summarize(rows,True,12)
    assert runner.binary_gate(b,{'net':1})
    assert not runner.binary_gate(b,{'net':-1})
