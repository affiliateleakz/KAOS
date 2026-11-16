"""Protect research chronology, exact settlement and invalid-data exclusion."""
import importlib.util
import json
from pathlib import Path
import zipfile
import numpy as np
import pandas as pd

spec=importlib.util.spec_from_file_location('broker_research',Path(__file__).resolve().parents[2]/'scripts/research_broker_edge.py')
research=importlib.util.module_from_spec(spec);spec.loader.exec_module(research)


def bars(count=420):
    result=[]
    for i in range(count):
        price=100+i*.01+np.sin(i/8)
        result.append((1699999980000+i*5000,price,price+.2,price-.1,price+.05))
    return result


def test_features_are_causal_and_warmup_is_segment_local():
    rows=bars();prefix=research.features([('TEST',rows[:370])]);full=research.features([('TEST',rows)])
    columns=research.FEATURES+['momentum','pullback','breakout','fade1.5','streak3']
    np.testing.assert_allclose(prefix[columns],full.iloc[:len(prefix)][columns],equal_nan=True)
    assert len(prefix)==71
    assert len(research.features([('TEST',rows),('TEST',rows[:100])]))==121


def test_settlement_requires_observed_future_and_avoids_overlap():
    ts=1699999980000
    f=pd.DataFrame({'decision':[ts+i*5000 for i in range(6)],'exit15':[102,98,102,98,np.nan,np.nan],
                    'entry':[100]*6,'asset':['TEST']*6,'segment':[0]*6})
    trades=research.trades(f,np.ones(6),15,ts,ts+100000)
    assert [r['entry_ts'] for r in trades]==[ts,ts+15000]
    assert [r['outcome'] for r in trades]==[1,-1]
    assert all(r['exit_ts']-r['entry_ts']==15000 for r in trades)
    assert research.trades(f,np.ones(6),15,ts,ts+15000)==[]


def test_conflicts_gaps_and_untrusted_trade_labels_are_audited(tmp_path):
    rows=[dict(zip(('ts','open','high','low','close'),r)) for r in bars(4)]
    conflict={**rows[1],'close':rows[1]['open']+.1}
    backup={'rawCandleHistory':{'byAsset':{'TEST':[rows[0],rows[0],rows[1],conflict,rows[3],{**rows[2],'close':-1}]}},
            'popupData':{'tradeRecords':[{'direction':'BUY','entryPrice':100,'exitPrice':101,'result':'loss'}]}}
    path=tmp_path/'input.zip'
    with zipfile.ZipFile(path,'w') as z:z.writestr('backup.json',json.dumps(backup))
    parts,quality,digest=research.load(path)
    assert quality['invalid_bars']==1 and quality['conflicting_timestamps']==1
    assert quality['valid_bars']==2 and len(parts)==2
    assert quality['recorded_trade_audit']['price_outcome_mismatch']==1
    assert len(digest)==64


def test_below_break_even_is_not_an_edge():
    rows=[{'asset':'TEST','utc_day':'2026-10-01','outcome':1}]*54+[{'asset':'TEST','utc_day':'2026-10-01','outcome':-1}]*46
    m=research.metrics(rows,36)
    assert m['pnl_at_payout']['0.8']<0 and m['wilson_lower_95']<1/1.8
    assert m['daily_cluster_bootstrap_lower_pnl95'] is None
