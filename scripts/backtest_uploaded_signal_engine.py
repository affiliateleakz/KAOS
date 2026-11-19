"""Offline replay of supplied pure JS rules. No third-party extension execution."""
import argparse,hashlib,json,subprocess,tempfile,csv
from pathlib import Path
import numpy as np
import backtest_video_strategies as replay
ROOT=Path(__file__).resolve().parents[1]


def replay_dataset(parts,indicator_path,engine_path,period):
    modes={mode+':'+level:[] for mode in ('sampled5','closed30') for level in ('low','mid','high')}
    kept=[(asset,rows) for asset,rows in parts if len(rows)>=72]
    with tempfile.TemporaryDirectory(prefix='kaos-pure-rule-') as work:
        source=Path(work)/'segments.jsonl';output=Path(work)/'signals.jsonl'
        with source.open('w') as f:
            for asset,rows in kept:f.write(json.dumps({'asset':asset,'rows':rows.tolist()},separators=(',',':'))+'\n')
        with source.open() as src,output.open('w') as dst:
            subprocess.run(['node',str(ROOT/'scripts/replay_uploaded_signal_engine.cjs'),str(indicator_path),str(engine_path)],stdin=src,stdout=dst,check=True)
        lines=output.read_text().splitlines()
        if len(lines)!=len(kept):raise ValueError('Signal stream count mismatch')
        for (asset,base),line in zip(kept,lines):
            data=json.loads(line)
            if data['asset']!=asset:raise ValueError('Asset mismatch')
            for mode,signals in data['signals'].items():
                for latency in (0,5):
                    available=-1
                    for sig in signals:
                        decision=sig['decision'];entry=decision+latency*1000;settle=entry+sig['expiry']*1000
                        if decision<period[0] or settle>=period[1] or entry<available:continue
                        ei=(entry-int(base[0,0]))//5000;si=(settle-int(base[0,0]))//5000
                        if ei<=0 or si>=len(base):continue
                        if int(base[ei,0])!=entry or int(base[si,0])!=settle:raise ValueError('Settlement misalignment')
                        actual=np.sign(base[si,1]-base[ei,1]);outcome=int(actual*sig['direction']);previous=np.sign(base[ei-1,4]-base[ei-1,1])
                        modes[mode].append({'asset':asset,'decision':decision,'entry':entry,'settle':settle,'expiry':sig['expiry'],'direction':sig['direction'],'confidence':sig['confidence'],'regime':sig['regime'],'outcome':outcome,'latency':latency,'call':int(actual),'put':int(-actual),'previous':int(actual*previous)})
                        available=settle
    return modes


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--indicators',type=Path,required=True);parser.add_argument('--engine',type=Path,required=True);parser.add_argument('--po',type=Path,required=True);parser.add_argument('--fresh',type=Path,required=True);args=parser.parse_args()
    directory=ROOT/'research/avalisa_rule_review_v1';out=directory/'results';out.mkdir(exist_ok=True)
    parts,po_meta=replay.load_po(args.po)
    print('Replaying source JS decision function on PO validation',flush=True)
    po=replay_dataset(parts,args.indicators,args.engine,(replay.stamp('2026-10-05 07:23:55'),replay.stamp('2026-10-05 18:10:50')))
    parts,proxy_meta=replay.load_proxy(args.fresh)
    print('Replaying source JS decision function on reserved Nov15-17 proxy',flush=True)
    fresh=replay_dataset(parts,args.indicators,args.engine,(replay.stamp('2026-11-15'),replay.stamp('2026-11-18')))
    result={'source_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (args.indicators,args.engine)},'plan_sha256':hashlib.sha256((directory/'plan.json').read_bytes()).hexdigest(),'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'harness_sha256':hashlib.sha256((ROOT/'scripts/replay_uploaded_signal_engine.cjs').read_bytes()).hexdigest(),'sources':{'po':po_meta,'fresh_proxy':proxy_meta},'extension_executed':False,'pure_decision_functions_executed':True,'live_approved':False,'results':{}}
    for dataset,rows in [('po_validation',po),('fresh_proxy',fresh)]:
        result['results'][dataset]={mode:{'base':replay.summarize(trades),'latency5':replay.summarize(trades,5),'passes_proxy_gate':replay.qualifies(replay.summarize(trades),trials=6,days=3) and replay.summarize(trades,5)['net_units']['0.8']>0} for mode,trades in rows.items()}
    (out/'summary.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    ledger=[{'mode':mode,**row} for mode,rows in fresh.items() for row in rows]
    with (out/'fresh_trades.csv').open('w') as f:
        writer=csv.DictWriter(f,fieldnames=list(ledger[0]) if ledger else ['mode']);writer.writeheader();writer.writerows(ledger)
    for mode,res in result['results']['fresh_proxy'].items():
        b=res['base'];print(mode,'trades',b['trades'],'win rate',b['win_rate'],'net80',b['net_units']['0.8'],'net92',b['net_units']['0.92'],'delay80',res['latency5']['net_units']['0.8'],'pass',res['passes_proxy_gate'],flush=True)


if __name__=='__main__':main()
