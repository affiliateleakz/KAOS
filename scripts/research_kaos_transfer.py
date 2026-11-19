"""Single preregistered external-market diagnostic; no order interface."""
import argparse,csv,hashlib,json
from pathlib import Path
import numpy as np
import research_kaos_swing as study
from backtest_all_timeframes import aggregate
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'research/kaos_transfer_v1'

def dump(name,data):(OUT/name).write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')

def qualifies(r):
    b=r['base'];bench=r['benchmarks']
    return bool(b['trades']>=150 and b['days']>=90 and b['PF'] is not None and b['PF']>=1.15 and sum(v>0 for v in b['asset_netR'].values())>=3 and b['lower_week_mean'] is not None and b['lower_week_mean']>0 and r['stress']['netR']>0 and all(m['meanR'] is not None and b['meanR']>m['meanR'] for m in bench.values()))

def main():
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);a=p.parse_args();plan=json.loads((OUT/'plan.json').read_text());manifest=json.loads((a.data/'manifest.json').read_text());prepared={14400:[]}
    if set(manifest['assets'])!=set(plan['assets']):raise ValueError('Market set changed')
    for asset,m in manifest['assets'].items():
        path=a.data/m['file']
        if hashlib.sha256(path.read_bytes()).hexdigest()!=m['sha256']:raise ValueError('Checksum mismatch')
        data=np.load(path,allow_pickle=False)
        if len(data)!=m['bars'] or np.any(np.diff(data[:,0])<=0):raise ValueError('Invalid source sequence')
        for seg in np.split(data,np.where(np.diff(data[:,0])!=3600000)[0]+1):
            if not len(seg):continue
            bars=aggregate(seg,14400,3600)
            if len(bars)>=250:prepared[14400].append((asset,seg,study.engine.swing_features(bars)))
    bounds=tuple(study.old.stamp(x) for x in plan['evaluation']);rows,r=study.swing_eval(prepared,(14400,'breakout20',3),bounds);r['base']=study.metrics(rows,15);r['diagnostic_gate_passed']=qualifies(r);r['executionEnabled']=False;r['original_studies_passed']=False
    r['by_asset']={asset:study.metrics([row for row in rows if row['asset']==asset]) for asset in plan['assets']}
    dump('result.json',r)
    dump('provenance.json',{'plan_sha256':hashlib.sha256((OUT/'plan.json').read_bytes()).hexdigest(),'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'engine_sha256':hashlib.sha256((ROOT/'research/kaos_swing_v1/strategy.py').read_bytes()).hexdigest(),'prior_engine_sha256':hashlib.sha256((ROOT/'research/kaos_candidate_v1/strategy.py').read_bytes()).hexdigest(),'sources':manifest,'single_configuration':True,'adaptive_external_asset_diagnostic':True,'executionEnabled':False})
    with (OUT/'trades.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else ['asset'],lineterminator='\n');w.writeheader();w.writerows(rows)
    print(json.dumps({'base':r['base'],'stress':r['stress'],'gate':r['diagnostic_gate_passed']}),flush=True)
if __name__=='__main__':main()
