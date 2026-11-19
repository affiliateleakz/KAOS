"""Static-rule reimplementation only. Never executes third-party browser bundle."""
import argparse,csv,hashlib,json
from pathlib import Path
import numpy as np
import pandas as pd
import backtest_video_strategies as replay
ROOT=Path(__file__).resolve().parents[1]


def cci_values(a):
    # Exact observed source OHLC4 / .02 formulation, not standard .015 HLC3 CCI.
    price=(a[:,1]+a[:,2]+a[:,3]+a[:,4])/4
    result=np.full(len(a),np.nan)
    for i in range(19,len(a)):
        window=price[i-19:i+1];mean=window.mean();mad=np.abs(window-mean).mean()
        result[i]=0 if mad==0 else (price[i]-mean)/(.02*mad)
    return result


def signals(a,family,variant):
    c=a[:,4];o=a[:,1];direction=np.zeros(len(a),dtype=int)
    if family=='bundle_cci':
        value=cci_values(a)
        buy=replay.cross(value,np.full(len(a),-115.));sell=replay.cross(np.full(len(a),115.),value)
        direction[buy]=1;direction[sell]=-1
    else:
        colors=np.sign(c-o);total=pd.Series(colors).rolling(4).sum().to_numpy()
        direction[total==4]=-1;direction[total==-4]=1
    direction[:300]=0
    return direction


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True);parser.add_argument('--po',type=Path,required=True);parser.add_argument('--october',type=Path,required=True);parser.add_argument('--fresh',type=Path,required=True);args=parser.parse_args()
    path=ROOT/'research/uploaded_bundle_v1';plan_path=path/'plan.json';plan=json.loads(plan_path.read_text());out=path/'results';out.mkdir(exist_ok=True)
    text=args.source.read_text()
    # Stop if the inspected source file was swapped for a different algorithm.
    for fragment in ('class CCIStrategy','class CandlesStrategy','upCross=-115,downCross=115','/(.02*mad)','(o+h+l+c)/4'):
        if fragment not in text:raise ValueError('Unexpected source bundle')
    replay.signals=signals
    configs=[{'family':family,'variant':'source','tf':tf,'expiry':expiry} for family in ('bundle_cci','bundle_four_candles') for tf in plan['sensitivity']['tf_seconds'] for expiry in plan['sensitivity']['expiry_seconds']]
    po,po_meta=replay.load_po(args.po);october,oct_meta=replay.load_proxy(args.october);results={}
    for name,rows in replay.replay(po,configs,{'po_validation':(replay.stamp('2026-10-05 07:23:55'),replay.stamp('2026-10-05 18:10:50'))}).items():
        results[name]={cid:{'base':replay.summarize(trades),'latency5':replay.summarize(trades,5)} for cid,trades in rows.items()}
    for name,rows in replay.replay(october,configs,{'october_proxy':(replay.stamp('2026-10-01'),replay.stamp('2026-10-08'))}).items():
        results[name]={cid:{'base':replay.summarize(trades),'latency5':replay.summarize(trades,5)} for cid,trades in rows.items()}
    fresh,fresh_meta=replay.load_proxy(args.fresh)
    primaries=[c for c in configs if c['tf']==60 and c['expiry']==60]
    raw=replay.replay(fresh,primaries,{'fresh_proxy':(replay.stamp('2026-11-08'),replay.stamp('2026-11-15'))})['fresh_proxy']
    results['fresh_proxy']={cid:{'base':replay.summarize(trades),'latency5':replay.summarize(trades,5),'passes_proxy_gate':replay.qualifies(replay.summarize(trades),trials=2,days=5) and replay.summarize(trades,5)['net_units']['0.8']>0} for cid,trades in raw.items()}
    report={'source_sha256':hashlib.sha256(args.source.read_bytes()).hexdigest(),'plan_sha256':hashlib.sha256(plan_path.read_bytes()).hexdigest(),'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'base_runner_sha256':hashlib.sha256(Path(replay.__file__).read_bytes()).hexdigest(),'sources':{'po':po_meta,'october_proxy':oct_meta,'fresh_proxy':fresh_meta},'results':results,'live_approved':False,'bundle_executed':False,'old_po_final_scored':False}
    (out/'summary.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    ledger=[{'config':cid,**row} for cid,rows in raw.items() for row in rows]
    with (out/'fresh_trades.csv').open('w') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(ledger[0]) if ledger else ['config']);writer.writeheader();writer.writerows(ledger)
    for cid,result in results['fresh_proxy'].items():print(cid,json.dumps(result['base']), 'DELAY',result['latency5']['net_units']['0.8'],'PASS',result['passes_proxy_gate'],flush=True)


if __name__=='__main__':main()
