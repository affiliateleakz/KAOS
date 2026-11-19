"""Frozen timeframe grid using user-supplied pure JS rules; no execution service."""
import argparse,csv,hashlib,json,subprocess,tempfile
from pathlib import Path
import numpy as np
from scipy.stats import binomtest
import backtest_video_strategies as old
ROOT=Path(__file__).resolve().parents[1]
TFS=[5,10,15,30,60,120,180,300,600,900,1800,3600,14400,86400]
LEVELS=['low','mid','high'];POLICIES=['source_adaptive','1_candle','2_candles','3_candles']

def aggregate(a,tf,base):
    if tf<base or tf%base:raise ValueError('Cannot infer finer candles')
    n=tf//base;start=(-int(a[0,0])//(base*1000))%n
    usable=(len(a)-start)//n*n
    if not usable:return np.empty((0,5))
    x=a[start:start+usable].reshape(-1,n,5)
    if np.any(np.diff(a[:,0])!=base*1000):raise ValueError('Input has gaps')
    return np.column_stack((x[:,0,0],x[:,0,1],x[:,:,2].max(1),x[:,:,3].min(1),x[:,-1,4]))

def settle(signals,a,tf,base,policy,delay,bounds):
    available=-1;rows=[];unresolved=0
    for decision,direction,adaptive in signals:
        expiry=adaptive if policy=='source_adaptive' else tf*int(policy[0])
        if decision<bounds[0] or decision>=bounds[1]:continue
        if expiry%base:unresolved+=1;continue
        entry=decision+delay*1000;end=entry+expiry*1000
        if entry<available or end>=bounds[1]:continue
        ei=(entry-int(a[0,0]))//(base*1000);si=(end-int(a[0,0]))//(base*1000)
        if ei<1 or si>=len(a):continue
        if a[ei,0]!=entry or a[si,0]!=end:raise ValueError('Misaligned fill')
        rows.append((entry,int(np.sign(a[si,1]-a[ei,1])*direction)))
        available=end
    return rows,unresolved

def stats(rows):
    w=sum(r[2]>0 for r in rows);l=sum(r[2]<0 for r in rows);ties=len(rows)-w-l;n=w+l
    days={};assets={}
    for asset,ts,outcome in rows:
        net=.9 if outcome>0 else -1 if outcome<0 else 0
        day=int(ts)//86400000;days[day]=days.get(day,0)+net;assets[asset]=assets.get(asset,0)+net
    vals=np.array(list(days.values()))
    boot=None
    if len(vals)>=2:
        rng=np.random.default_rng(55)
        boot=float(np.quantile(rng.choice(vals,(2000,len(vals)),replace=True).mean(1),.025))
    return {'trades':len(rows),'wins':w,'losses':l,'ties':ties,'decided':n,'win_rate':w/n if n else None,'wilson_lower':old.wilson(w,n) if n else None,'p90':float(binomtest(w,n,1/1.9,alternative='greater').pvalue) if n else None,'days':len(days),'net':{str(p):round(w*p-l,6) for p in (.7,.8,.9,.92)},'day_bootstrap_lower_mean90':boot,'asset_net90':{k:round(v,6) for k,v in assets.items()}}

def qualifies(b,delayed,days,correct=False):
    return bool(b['decided']>=200 and b['days']>=days and b['wilson_lower']>1/1.9 and (not correct or b['p90']<.05/168) and b['day_bootstrap_lower_mean90'] is not None and b['day_bootstrap_lower_mean90']>0 and sum(v>0 for v in b['asset_net90'].values())>=2 and delayed['net']['0.9']>0)

def run(parts,tfs,base,phases,ip,ep):
    trades={f'{tf}:{level}:{policy}':{phase:{'base':[],'delayed':[],'unresolved':0} for phase in phases} for tf in tfs for level in LEVELS for policy in POLICIES}
    with tempfile.TemporaryDirectory(prefix='kaos-tf-') as tmp:
        src=Path(tmp)/'in';dst=Path(tmp)/'out';kept=[]
        with src.open('w') as f:
            for asset,a in parts:
                for tf in tfs:
                    bars=aggregate(a,tf,base)
                    if len(bars)<12:continue
                    kept.append((asset,a,tf))
                    f.write(json.dumps({'asset':asset,'tf':tf,'rows':bars.tolist()},separators=(',',':'))+'\n')
        with src.open() as fi,dst.open('w') as fo:
            subprocess.run(['node',str(ROOT/'scripts/replay_timeframe_engine.cjs'),str(ip),str(ep)],stdin=fi,stdout=fo,check=True)
        with dst.open() as f:
            for (asset,a,tf),line in zip(kept,f,strict=True):
                data=json.loads(line)
                if data['asset']!=asset or data['tf']!=tf:raise ValueError('Stream mismatch')
                for level,signals in data['signals'].items():
                    for policy in POLICIES:
                        config=trades[f'{tf}:{level}:{policy}']
                        for phase,bounds in phases.items():
                            for label,delay in [('base',0),('delayed',base)]:
                                rows,unresolved=settle(signals,a,tf,base,policy,delay,bounds)
                                config[phase][label].extend((asset,ts,outcome) for ts,outcome in rows)
                                if not delay:config[phase]['unresolved']+=unresolved
    return {key:{phase:{'base':stats(r['base']),'delayed':stats(r['delayed']),'unresolved_expiry_signals':r['unresolved']} for phase,r in value.items()} for key,value in trades.items()}

def main():
    p=argparse.ArgumentParser();p.add_argument('--indicators',type=Path,required=True);p.add_argument('--engine',type=Path,required=True);p.add_argument('--minutes',type=Path,required=True);args=p.parse_args()
    out=ROOT/'research/all_timeframes_v1';manifest=json.loads((args.minutes/'manifest.json').read_text());parts=[]
    for path in sorted(args.minutes.glob('*.npy')):
        a=np.load(path,allow_pickle=False)
        for seg in np.split(a,np.where(np.diff(a[:,0])!=60000)[0]+1):
            if len(seg):parts.append((path.stem,seg))
    phases={k:tuple(old.stamp(v) for v in dates) for k,dates in {'development':('2025-01-01','2026-01-01'),'validation':('2026-01-01','2026-10-01'),'confirmation':('2026-10-01','2026-11-01')}.items()}
    print('Long grid',sum(len(a) for _,a in parts),'minute candles',flush=True)
    long=run(parts,[tf for tf in TFS if tf>=60],60,phases,args.indicators,args.engine)
    (out/'long_results.json').write_text(json.dumps(long,indent=2)+'\n')
    candidates=[key for key,r in long.items() if qualifies(r['validation']['base'],r['validation']['delayed'],30,True)]
    selected=sorted(candidates,key=lambda k:(-long[k]['validation']['base']['wilson_lower'],k))[0] if candidates else None
    print('Frozen validation selection:',selected,flush=True)
    shortparts=[];sources=[]
    for name in ['public-candles-20261001','video-proxy-holdout-20261101','bundle-proxy-holdout-20261108','avalisa-proxy-20261115']:
        segments,meta=old.load_proxy(ROOT.parent/name);shortparts.extend(segments);sources.append(meta)
    po=Path('/workspace/attachments/d2569f6a-510b-414f-b6a7-a9bb07cac2f6/KAOS_ALL_DATA_2026-10-08T18-42-12.zip')
    poparts,pometa=old.load_po(po)
    # Preserve the previously reserved PO final. Separate assets from crypto proxies.
    cutoff=old.stamp('2026-10-05 18:10:50')
    shortparts.extend(('PO:'+asset,a[a[:,0]<cutoff]) for asset,a in poparts if np.any(a[:,0]<cutoff))
    print('Short grid',sum(len(a) for _,a in shortparts),'5s candles',flush=True)
    short=run(shortparts,[5,10,15,30],5,{'descriptive':(0,old.stamp('2026-11-18'))},args.indicators,args.engine)
    result={'selected_on_validation':selected,'confirmation_pass':qualifies(long[selected]['confirmation']['base'],long[selected]['confirmation']['delayed'],15) if selected else False,'configurations':len(long)+len(short),'source_hashes':{str(path.name):hashlib.sha256(path.read_bytes()).hexdigest() for path in [args.indicators,args.engine,out/'plan.json',Path(__file__),ROOT/'scripts/replay_timeframe_engine.cjs']},'minute_manifest':manifest,'short_sources':sources,'po_source':pometa,'long':long,'short':short}
    (out/'summary.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    with (out/'matrix.csv').open('w') as f:
        fields=['config','phase','trades','wins','losses','ties','win_rate','wilson_lower','days','net70','net80','net90','net92','delayed_net90','unresolved_expiry_signals'];w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for key,value in {**long,**short}.items():
            for phase,r in value.items():
                b=r['base'];w.writerow({'config':key,'phase':phase,**{k:b[k] for k in ['trades','wins','losses','ties','win_rate','wilson_lower','days']},**{'net'+str(int(float(k)*100)):v for k,v in b['net'].items()},'delayed_net90':r['delayed']['net']['0.9'],'unresolved_expiry_signals':r['unresolved_expiry_signals']})
    print('Complete:',result['configurations'],'selected',selected,'confirmation pass',result['confirmation_pass'],flush=True)
if __name__=='__main__':main()
