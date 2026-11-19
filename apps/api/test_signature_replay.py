"""Replay provenance, gap handling, and parity with the extension's actual signature engine."""
import json
import random
import csv
import subprocess
from pathlib import Path
import pytest
import kaos_signature as signature
from signature_backtest import normalized,replay


def candles(n=650):
    rng=random.Random(17);rows=[];price=100
    for i in range(n):
        close=price+rng.uniform(-.2,.2)
        rows.append({'ts':1699999980000+i*5000,'closeTs':1699999980000+(i+1)*5000,'open':price,'high':max(price,close)+rng.random()*.15,'low':min(price,close)-rng.random()*.15,'close':close});price=close
    return rows


def test_python_signature_matches_actual_javascript_for_closed_history():
    path=Path(__file__).parents[1]/'extension/candidate7b_strategy.js'
    script="const vm=require('node:vm'),fs=require('node:fs');const ctx={window:{}};vm.createContext(ctx);vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),ctx);const rows=JSON.parse(fs.readFileSync(0,'utf8'));process.stdout.write(JSON.stringify(rows.map(r=>ctx.window.KAOSCandidate7B.signal(r))));"
    rows=candles();windows=[rows[:i] for i in range(300,650,7)]
    root=Path(__file__).resolve().parents[2]
    recorded=json.loads((root/'research/signature_sr11/data/combined_5s.json').read_text())['markets']
    positive=[]
    with (root/'research/signature_sr11/audit/trades.csv').open() as handle:
        for trade in csv.DictReader(handle):
            rows=normalized(recorded[trade['symbol']]);end=next(i for i,r in enumerate(rows) if r['ts']==int(trade['signal_ts']))
            start=end
            while start>0 and rows[start]['ts']==rows[start-1]['ts']+5000:start-=1
            positive.append([{**r,'closeTs':r['ts']+5000} for r in rows[start:end+1]])
    assert len(positive)==5
    windows+=positive
    expected=json.loads(subprocess.run(['node','-e',script,str(path)],input=json.dumps(windows),text=True,capture_output=True,check=True).stdout)
    assert all(expected[-len(positive):]), "Recorded entry windows must exercise real signals"
    for window,js in zip(windows,expected):
        py=signature.evaluate(window)
        assert bool(py)==bool(js)
        if js:assert (py['engine'],py['direction'],py['expiry'])==(js['engine'],js['dir'],js['expiry'])


def test_replay_uses_current_engine_and_never_claims_live_approval():
    rows=candles();report=replay({'TEST':rows})
    assert report['version']=='SR1.1' and report['live_approved'] is False
    assert report['broker_execution_verified'] is False
    by_ts={r['ts']:r for r in rows}
    for trade in report['trades']:
        assert trade['entry_ts']==trade['signal_ts']+5000
        assert trade['exit_ts']-trade['entry_ts'] in (15000,20000,25000)
        assert trade['entry']==by_ts[trade['entry_ts']]['open']
    assert replay({'TEST':rows[:200]+rows[220:]})['gaps']==1
    assert normalized(rows+[rows[0]])==normalized(rows)
    with pytest.raises(ValueError):normalized(rows+[{**rows[0],'close':-1}])
