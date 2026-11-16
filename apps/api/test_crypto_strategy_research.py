"""Research trade replay keeps future prices out of decisions and stresses entry costs."""
import importlib.util
import sys
from pathlib import Path
import numpy as np
import pandas as pd

scripts=Path(__file__).resolve().parents[2]/'scripts'
spec=importlib.util.spec_from_file_location('research_broker_edge',scripts/'research_broker_edge.py')
base=importlib.util.module_from_spec(spec);sys.modules[spec.name]=base;spec.loader.exec_module(base)
spec=importlib.util.spec_from_file_location('crypto_research',scripts/'research_crypto_strategy.py')
crypto=importlib.util.module_from_spec(spec);spec.loader.exec_module(crypto)


def frame():
    ts=1791244800000
    f=pd.DataFrame({'decision':ts+np.arange(8)*5000,'asset':['TEST']*8,'segment':[0]*8})
    for shift in (1,2,4,5,7,8,13,14):f['open_shift'+str(shift)]=100.005 if shift in (4,5) else 100.
    f.loc[5:,'open_shift4']=np.nan
    return f


def test_next_open_settlement_no_overlap_and_boundary_purge():
    f=frame();start=int(f.decision.iloc[0]);side=np.ones(len(f))
    result=crypto.replay(f,side,15,start,start+100000)
    assert [r['entry_ts'] for r in result]==[start,start+15000]
    assert all(r['exit_ts']-r['entry_ts']==15000 for r in result)
    assert crypto.replay(f,side,15,start,start+15000)==[]


def test_adverse_entry_changes_proxy_outcomes_in_conservative_direction():
    f=frame();start=int(f.decision.iloc[0]);side=np.ones(len(f))
    plain=crypto.replay(f,side,15,start,start+100000)
    stress=crypto.replay(f,side,15,start,start+100000,adverse_bps=1)
    assert plain[0]['outcome']==1 and stress[0]['outcome']==-1
    assert stress[0]['entry']>plain[0]['entry']
    delayed=crypto.replay(f,side,15,start,start+100000,delay=1)
    assert delayed[0]['entry_ts']==plain[0]['entry_ts']+5000
    assert delayed[0]['exit_ts']==plain[0]['exit_ts']+5000


def test_validation_eligibility_requires_two_profitable_days_and_markets():
    m={'decided':200,'days':2,'by_asset':{'A':{},'B':{}},'daily_pnl':{'day1':1,'day2':1}}
    assert crypto.eligible(m)
    assert not crypto.eligible({**m,'daily_pnl':{'day1':1,'day2':-1}})
    assert not crypto.eligible({**m,'by_asset':{'A':{}}})


def test_paper_predictor_is_scoped_stale_safe_and_future_invariant():
    spec=importlib.util.spec_from_file_location('paper_strategy',scripts.parent/'research/crypto_strategy_v1/strategy.py')
    paper=importlib.util.module_from_spec(spec);spec.loader.exec_module(paper)
    model=paper.ResearchStrategy();start=1791244800000
    rows=[]
    for i in range(350):
        price=100+np.sin(i/8)+i*.001
        rows.append({'ts':start+i*5000,'closeTs':start+(i+1)*5000,'open':price,'high':price+.2,'low':price-.1,'close':price+.05})
    cutoff=rows[-1]['closeTs'];first=model.predict('BTCUSDT',rows,cutoff)
    assert first['executionEnabled'] is False and first['researchOnly'] is True
    future={**rows[-1],'ts':cutoff,'closeTs':cutoff+5000,'open':1,'high':2000,'low':.1,'close':1500}
    assert model.predict('BTCUSDT',rows+[future],cutoff)==first
    assert model.predict('BTCUSDT',rows,cutoff+10000)['direction']=='HOLD'
    assert model.predict('EURUSD_otc',rows,cutoff)['direction']=='HOLD'
    assert model.predict('BTCUSDT',rows[:100],rows[99]['closeTs'])['direction']=='HOLD'
