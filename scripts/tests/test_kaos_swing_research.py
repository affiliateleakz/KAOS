"""Protect execution chronology, self-financing and holdout gates."""
import importlib.util,sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'))
spec=importlib.util.spec_from_file_location('swing',ROOT/'research/kaos_swing_v1/strategy.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def arrays():
    a=np.column_stack((np.arange(200)*3600000,np.full((200,4),100.)))
    a[:,2]=101;a[:,3]=99
    f=pd.DataFrame({'ts':np.arange(200)*3600000,'atr':np.ones(200),'highclose20':np.full(200,100.),'close':np.full(200,100.),'ema50':np.full(200,95.),'low10':np.full(200,90.)})
    return a,f

def single_signal(monkeypatch):monkeypatch.setattr(m.prior,'spot_signals',lambda f,family:np.arange(len(f))==0)

def test_trailing_stop_only_applies_next_hour(monkeypatch):
    single_signal(monkeypatch);a,f=arrays();f.loc[1,'highclose20']=110
    r=m.swing_replay('BTC',a,f,3600,'breakout20',3,(0,9999999999))[0]
    assert r['exit']==7200000 and r['reason']=='gap_stop'
    assert r['exit_price']==pytest.approx(100*(1-.0002))

def test_signal_exit_occurs_after_close(monkeypatch):
    single_signal(monkeypatch);a,f=arrays();f.atr=5.;f.loc[1,'close']=90;a[1,3]=88;a[1,4]=90;a[2,1]=94
    r=m.swing_replay('BTC',a,f,3600,'breakout20',3,(0,9999999999))[0]
    assert r['exit']==7200000 and r['reason']=='signal_exit'
    assert r['exit_price']==pytest.approx(94*(1-.0002))

def test_fee_budget_and_holding_split(monkeypatch):
    single_signal(monkeypatch);a,f=arrays();f.atr=.1
    assert not m.swing_replay('BTC',a,f,3600,'breakout20',3,(0,9999999999))
    f.atr=1.
    assert not m.swing_replay('BTC',a,f,3600,'breakout20',3,(0,100*3600000))

def test_rebalance_cannot_spend_missing_cash():
    cash,q=m.rebalance(1.,np.array([0.]),np.array([100.]),np.array([1.]),.01)
    assert cash==pytest.approx(0.) and q[0]==pytest.approx(1/101)
    cash,q=m.rebalance(cash,q,np.array([100.]),np.array([0.]),.01)
    assert cash==pytest.approx(.99/1.01) and q[0]==pytest.approx(0.)

def test_rebalance_nonnegative_and_zero_cost_conservation():
    cash,q=m.rebalance(.2,np.array([.003,.005]),np.array([100.,100.]),np.array([.5,.5]),0)
    assert cash>=0 and np.all(q>=0)
    assert cash+q@np.array([100.,100.])==pytest.approx(1.)

def test_weekly_decision_does_not_use_forming_day():
    monday=int(pd.Timestamp('2023-01-02',tz='UTC').timestamp()*1000)
    times=monday+np.arange(10)*3600000;prices=np.full((10,2),100.);panel=(['A','B'],times,prices,prices)
    context={('A',monday):(100.,90.,.5,.5)} # Monday not complete: must not enter.
    p=m.portfolio_replay(panel,context,20,1,(monday,monday+11*3600000))
    assert p['strategy']==[1.]*10
    context[('A',monday-86400000)]=(100.,90.,.1,.1)
    p=m.portfolio_replay(panel,context,20,1,(monday,monday+11*3600000))
    assert p['strategy'][-1]==pytest.approx((1-.0012)/(1+.0012))

def test_portfolio_prefix_causal_and_delayed_rebalance():
    monday=int(pd.Timestamp('2023-01-02',tz='UTC').timestamp()*1000);times=monday+np.arange(20)*3600000;p=np.full((20,1),100.);context={('A',monday-86400000):(100.,90.,.1,.1)}
    early=m.portfolio_replay((['A'],times[:10],p[:10],p[:10]),context,20,1,(monday,monday+30*3600000))
    p[10:]=200
    full=m.portfolio_replay((['A'],times,p,p),context,20,1,(monday,monday+30*3600000))
    assert early['strategy'][:-1]==full['strategy'][:9] # Last observation has forced liquidation cost.
    stress=m.portfolio_replay((['A'],times,p,p),context,20,1,(monday,monday+30*3600000),True)
    assert stress['strategy'][0]==1. and stress['strategy'][1]<1.

def test_gap_exit_uses_next_observed_price():
    monday=int(pd.Timestamp('2023-01-02',tz='UTC').timestamp()*1000);times=monday+np.array([0,1,3])*3600000;p=np.array([[100.],[100.],[50.]])
    context={('A',monday-86400000):(100.,90.,.1,.1)}
    r=m.portfolio_replay((['A'],times,p,p),context,20,1,(monday,monday+10*3600000))
    assert r['gap_liquidations']==1 and r['strategy'][-1]<.51

def test_failed_excess_or_stress_blocks_portfolio_qualification():
    import research_kaos_swing as runner
    base={'weeks':104,'strategy':{'return':.2,'max_drawdown':.1,'annual_returns':{'2023':.1,'2024':.1}},'matched':{'return':.1},'lower_weekly_excess':.001}
    assert runner.portfolio_gate({'base':base,'stress':{'strategy':{'return':.1}}})
    assert not runner.portfolio_gate({'base':base,'stress':{'strategy':{'return':-.1}}})
    assert not runner.portfolio_gate({'base':{**base,'lower_weekly_excess':-.001},'stress':{'strategy':{'return':.1}}})


def fake_archive(rows):
    import csv,io,zipfile
    content=io.StringIO();csv.writer(content).writerows(rows);buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w') as z:z.writestr('bars.csv',content.getvalue())
    return buf.getvalue()


def fake_http(monkeypatch,payload,missing=False,wrong_checksum=False):
    import collect_swing_history as collector
    import hashlib
    class Response:
        def __init__(self,checksum):
            self.status_code=404 if missing and checksum else 200
            self.text=('0'*64 if wrong_checksum else hashlib.sha256(payload).hexdigest())+'  bars.zip'
            self.content=payload
        def raise_for_status(self):
            if self.status_code!=200:raise RuntimeError('HTTP failure')
    class Client:
        def __init__(self,**kwargs):pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def get(self,url):return Response(url.endswith('.CHECKSUM'))
    monkeypatch.setattr(collector.httpx,'Client',Client)
    return collector


def test_collector_records_bad_alignment_without_rounding(monkeypatch,tmp_path):
    payload=fake_archive([[0,100,101,99,100,0,0,0,3],[3600001,100,101,99,100,0,0,0,3],[7200000,100,101,99,100,0,0,0,0]])
    collector=fake_http(monkeypatch,payload)
    asset,rows,meta=collector.fetch(('BTCUSDT',2018,1,tmp_path))
    assert len(rows)==1 and rows[0][0]==0
    assert meta['rejectedBars']==[{'ts':3600001,'reason':'unaligned_or_invalid_OHLC'}]
    assert meta['checksumVerified']


def test_missing_prelisting_archive_remains_missing(monkeypatch,tmp_path):
    collector=fake_http(monkeypatch,b'',missing=True)
    _,rows,meta=collector.fetch(('SOLUSDT',2018,1,tmp_path))
    assert rows==[] and meta['missingArchive'] and meta['httpStatus']==404


def test_collector_rejects_wrong_checksum(monkeypatch,tmp_path):
    collector=fake_http(monkeypatch,fake_archive([[0,100,101,99,100,0,0,0,3]]),wrong_checksum=True)
    with pytest.raises(ValueError,match='Checksum'):collector.fetch(('BTCUSDT',2018,1,tmp_path))
