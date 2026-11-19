"""Causality, next-open fills and gap handling for offline video research."""
import importlib.util
from pathlib import Path
import numpy as np
import pytest
spec=importlib.util.spec_from_file_location('video_replay',Path(__file__).resolve().parents[1]/'backtest_video_strategies.py')
replay=importlib.util.module_from_spec(spec);spec.loader.exec_module(replay)


def bars(n=330):
    a=np.array([[i*5000,100,101,99,100] for i in range(n)],dtype=float)
    return a


def test_aggregation_only_complete_aligned_bars():
    a=bars(10)[1:]
    result=replay.aggregate(a,15)
    assert list(result[:,0])==[15000,30000]
    assert list(result[:,1])==[100,100]


def test_indicator_prefix_invariant_to_future_prices():
    rng=np.random.default_rng(1);a=bars(700);c=100+np.cumsum(rng.normal(0,.1,700));a[:,1]=c;a[:,2]=c+.2;a[:,3]=c-.2;a[:,4]=c
    for family,variants in replay.VARIANTS.items():
        for variant in variants:
            assert np.array_equal(replay.signals(a[:500],family,variant),replay.signals(a,family,variant)[:500])


def test_next_open_and_exact_settlement_no_gap_bridge(monkeypatch):
    def signal(a,*args):
        s=np.zeros(len(a),dtype=int)
        if len(a)>300:s[300]=1
        return s
    monkeypatch.setattr(replay,'signals',signal)
    a=bars(305);a[300,4]=150;a[300,2]=151;a[304,1]=101;a[304,2]=102
    config={'family':'macd_rsi','variant':'strict','tf':5,'expiry':15}
    result=replay.replay([('ASSET',a)],[config],{'test':(0,2000000)})['test'][replay.config_id(config)]
    row=next(r for r in result if r['latency']==0)
    assert row['entry']==301*5000 and row['settle']==304*5000 and row['outcome']==1
    split=[('ASSET',a[:303]),('ASSET',a[304:])]
    assert not replay.replay(split,[config],{'test':(0,2000000)})['test'][replay.config_id(config)]


def test_payout_math_and_tie_refunds():
    rows=[{'outcome':x,'latency':0,'entry':i*5000,'asset':'ASSET','call':x,'put':-x,'previous':x} for i,x in enumerate([1,1,-1,0])]
    result=replay.summarize(rows)
    assert result['ties']==1 and result['net_units']['0.8']==pytest.approx(.6)
    assert result['win_rate']==2/3
