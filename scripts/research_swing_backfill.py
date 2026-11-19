"""Two unchanged rule settings on additional historical regimes; sealed final."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
import research_kaos_swing as study
from backtest_all_timeframes import aggregate
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'research/kaos_swing_v1/backfill'

def dump(name,value):(OUT/name).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')

def main():
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,nargs=2,required=True);args=p.parse_args();OUT.mkdir(exist_ok=True);plan_path=OUT.parent/'backfill_plan.json';plan=json.loads(plan_path.read_text());merged={};manifests=[]
    for directory in args.data:
        manifest=json.loads((directory/'manifest.json').read_text());manifests.append(manifest)
        for asset,m in manifest['assets'].items():
            path=directory/m['file']
            if hashlib.sha256(path.read_bytes()).hexdigest()!=m['sha256']:raise ValueError('Checksum mismatch')
            a=np.load(path,allow_pickle=False)
            if len(a)!=m['bars']:raise ValueError('Source count mismatch')
            merged.setdefault(asset,[]).append(a)
    prepared={14400:[]}
    for asset,chunks in merged.items():
        a=np.concatenate(chunks);a=a[np.argsort(a[:,0])]
        if np.any(np.diff(a[:,0])<=0):raise ValueError('Duplicate/out-of-order data')
        for seg in np.split(a,np.where(np.diff(a[:,0])!=3600000)[0]+1):
            if not len(seg):continue
            bars=aggregate(seg,14400,3600)
            if len(bars)>=250:prepared[14400].append((asset,seg,study.engine.swing_features(bars)))
    dump('provenance.json',{'plan_sha256':hashlib.sha256(plan_path.read_bytes()).hexdigest(),'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'engine_sha256':hashlib.sha256((OUT.parent/'strategy.py').read_bytes()).hexdigest(),'study_runner_sha256':hashlib.sha256((ROOT/'scripts/research_kaos_swing.py').read_bytes()).hexdigest(),'sources':manifests,'conditional_followup':True,'executionEnabled':False})
    validation=tuple(study.old.stamp(x) for x in plan['validation']);results={}
    for mult in [3,4]:
        key=f'14400:breakout20:{mult}';rows,r=study.swing_eval(prepared,(14400,'breakout20',mult),validation);r['base']=study.metrics(rows,14)
        r['eligible']=bool(study.swing_gate(r) and r['base']['trades']>=300 and r['base']['days']>=150);results[key]=r
        print('BACKFILL',key,r['base'],'stress',r['stress']['netR'],'eligible',r['eligible'],flush=True)
    dump('validation.json',results);eligible=[key for key,r in results.items() if r['eligible']];selected=sorted(eligible,key=lambda k:(-results[k]['base']['lower_week_mean'],k))[0] if eligible else None
    dump('selection.json',{'selected':selected,'frozen_before_confirmation':True,'confirmation_evaluated':selected is not None,'executionEnabled':False});final={'qualified':False,'state':'not_opened_no_backfill_candidate','executionEnabled':False}
    if selected:
        mult=int(selected.split(':')[-1]);bounds=tuple(study.old.stamp(x) for x in plan['confirmation']);rows,r=study.swing_eval(prepared,(14400,'breakout20',mult),bounds,set(plan['confirmation_assets']));final={'selected':selected,**r,'qualified':study.swing_gate(r,True),'executionEnabled':False};dump('final_trades.json',rows)
    dump('confirmation.json',final)
    dump('paper_candidate.json',{'qualified_for_further_paper_research':final['qualified'],'selected':selected,'executionEnabled':False,'researchOnly':True,'trainedAI':False,'note':'Adaptive historical research with correlated assets; no established live edge or broker integration.'})
    print('COMPLETE selected',selected,'final qualified',final['qualified'],flush=True)
if __name__=='__main__':main()
