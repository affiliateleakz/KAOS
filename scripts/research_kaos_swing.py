"""Frozen hourly swing/weekly portfolio comparison. No live execution."""
import argparse,hashlib,importlib.util,itertools,json
from pathlib import Path
import numpy as np
import pandas as pd
import backtest_video_strategies as old
from backtest_all_timeframes import aggregate
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'research/kaos_swing_v1'
spec=importlib.util.spec_from_file_location('swing_engine',OUT/'strategy.py');engine=importlib.util.module_from_spec(spec);spec.loader.exec_module(engine)

def dump(name,value):(OUT/name).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')

def bootstrap(values,adjust=1,block=1):
    x=np.asarray(values)
    if len(x)<2:return None
    rng=np.random.default_rng(619);n=len(x);starts=rng.integers(n,size=(5000,(n+block-1)//block));indices=(starts[:,:,None]+np.arange(block))%n
    means=x[indices.reshape(5000,-1)[:,:n]].mean(1)
    return float(np.quantile(means,.05/adjust if adjust>1 else .025))

def metrics(rows,adjust=1):
    net=np.array([r['netR'] for r in rows]);weeks={};assets={}
    for r in rows:
        week=(r['entry']+3*86400000)//(7*86400000);weeks[week]=weeks.get(week,0)+r['netR'];assets[r['asset']]=assets.get(r['asset'],0)+r['netR']
    win=float(net[net>0].sum());loss=float(-net[net<0].sum())
    return {'trades':len(rows),'days':len(set(r['entry']//86400000 for r in rows)),'weeks':len(weeks),'netR':float(net.sum()),'meanR':float(net.mean()) if len(net) else None,'PF':win/loss if loss else None,'asset_netR':assets,'lower_week_mean':bootstrap(list(weeks.values()),adjust)}

def swing_gate(r,final=False):
    m=r['base'];return bool(m['trades']>=(60 if final else 150) and m['days']>=(40 if final else 90) and m['PF'] is not None and m['PF']>=(1.10 if final else 1.15) and m['netR']>0 and sum(v>0 for v in m['asset_netR'].values())>=(2 if final else 4) and m['lower_week_mean'] is not None and m['lower_week_mean']>0 and r['stress']['netR']>0 and all(m['meanR']>b['meanR'] for b in r['benchmarks'].values() if b['meanR'] is not None))

def swing_eval(prepared,config,bounds,assets=None):
    tf,family,mult=config;rows=[];stress=[];bench={key:[] for key in ['always_long','trend_long']}
    for asset,a,f in prepared[tf]:
        if assets is not None and asset not in assets:continue
        rows+=engine.swing_replay(asset,a,f,tf,family,mult,bounds)
        stress+=engine.swing_replay(asset,a,f,tf,family,mult,bounds,True)
        for key in bench:bench[key]+=engine.swing_replay(asset,a,f,tf,key,mult,bounds)
    return rows,{'base':metrics(rows,1 if assets else 12),'stress':metrics(stress),'benchmarks':{k:metrics(v) for k,v in bench.items()}}

def portfolio_metrics(paths,adjust=1):
    index=pd.to_datetime(paths['times'],unit='ms',utc=True);weekly={};out={}
    for key in ['strategy','matched','passive']:
        a=np.array(paths[key]);s=pd.Series(a,index=index);w=s.resample('W-SUN').last().dropna();ret=w/np.r_[1.,w.to_numpy()[:-1]]-1;weekly[key]=ret.to_numpy()
        annual=s.resample('YE').last().dropna();annualret=annual/np.r_[1.,annual.to_numpy()[:-1]]-1
        out[key]={'return':float(a[-1]-1) if len(a) else 0.,'max_drawdown':float(np.max(1-a/np.maximum.accumulate(np.r_[1.,a])[1:])) if len(a) else 0.,'annual_returns':{str(k.year):float(v) for k,v in annualret.items()}}
    excess=weekly['strategy']-weekly['matched'];out['weeks']=len(excess);out['lower_weekly_excess']=bootstrap(excess,adjust,4);out['mean_weekly_excess']=float(excess.mean()) if len(excess) else None;out['gap_liquidations']=paths['gap_liquidations'];return out

def portfolio_gate(r,final=False):
    m=r['base'];a=m['strategy'];return bool(m['weeks']>=(40 if final else 52) and a['return']>0 and a['max_drawdown']<=.25 and (final or all(a['annual_returns'].get(str(y),0)>0 for y in [2023,2024])) and r['stress']['strategy']['return']>0 and a['return']>m['matched']['return'] and m['lower_weekly_excess'] is not None and m['lower_weekly_excess']>0)

def panel_for(raw,assets):
    common=sorted(set.intersection(*(set(raw[a][:,0].astype(np.int64)) for a in assets)));times=np.array(common,dtype=np.int64);op=[];cp=[]
    for asset in assets:
        a=raw[asset];idx=np.searchsorted(a[:,0],times);op.append(a[idx,1]);cp.append(a[idx,4])
    return assets,times,np.array(op).T,np.array(cp).T

def main():
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);args=p.parse_args();plan=json.loads((OUT/'plan.json').read_text());manifest=json.loads((args.data/'manifest.json').read_text());raw={};parts=[]
    for asset,m in manifest['assets'].items():
        path=args.data/m['file']
        if hashlib.sha256(path.read_bytes()).hexdigest()!=m['sha256']:raise ValueError('Checksum mismatch')
        a=np.load(path,allow_pickle=False)
        if len(a)!=m['bars'] or np.any(np.diff(a[:,0])<=0):raise ValueError('Invalid order/count')
        raw[asset]=a
        parts.extend((asset,s) for s in np.split(a,np.where(np.diff(a[:,0])!=3600000)[0]+1) if len(s))
    dump('provenance.json',{'source':manifest,'plan_sha256':hashlib.sha256((OUT/'plan.json').read_bytes()).hexdigest(),'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'engine_sha256':hashlib.sha256((OUT/'strategy.py').read_bytes()).hexdigest(),'prior_engine_sha256':hashlib.sha256((ROOT/'research/kaos_candidate_v1/strategy.py').read_bytes()).hexdigest(),'executionEnabled':False})
    prepared={tf:[] for tf in [3600,14400]}
    for asset,a in parts:
        for tf in prepared:
            bars=aggregate(a,tf,3600)
            if len(bars)>=250:prepared[tf].append((asset,a,engine.swing_features(bars)))
    validation=tuple(old.stamp(x) for x in plan['validation']);final=tuple(old.stamp(x) for x in plan['confirmation']);new=set(plan['confirmation_assets']);results={};configs={}
    for tf,family,mult in itertools.product([3600,14400],['breakout20','pullback20'],[3,4]):
        key=f'{tf}:{family}:{mult}';configs[key]=(tf,family,mult);_,r=swing_eval(prepared,configs[key],validation);r['eligible']=swing_gate(r);results[key]=r;print('SWING',key,r['base']['trades'],round(r['base']['netR'],2),'eligible',r['eligible'],flush=True)
    dump('swing_validation.json',results);eligible=[k for k,r in results.items() if r['eligible']];selected=sorted(eligible,key=lambda k:(-results[k]['base']['lower_week_mean'],k))[0] if eligible else None
    dump('swing_selection.json',{'selected':selected,'frozen_before_final':True,'confirmation_evaluated':selected is not None});confirmation={'qualified':False,'state':'not_opened'}
    if selected:
        rows,r=swing_eval(prepared,configs[selected],final,new);confirmation={'selected':selected,**r,'qualified':swing_gate(r,True)};dump('swing_final_trades.json',rows)
    dump('swing_confirmation.json',confirmation)
    context=engine.daily_context(parts,aggregate);panel=panel_for(raw,sorted(raw));momentum={}
    for lookback,top in itertools.product([20,60],[1,2]):
        key=f'{lookback}:{top}';paths=engine.portfolio_replay(panel,context,lookback,top,validation);stress=engine.portfolio_replay(panel,context,lookback,top,validation,True);r={'base':portfolio_metrics(paths,12),'stress':portfolio_metrics(stress)};r['eligible']=portfolio_gate(r);momentum[key]=r;print('MOMENTUM',key,'return',r['base']['strategy']['return'],'eligible',r['eligible'],flush=True)
    dump('momentum_validation.json',momentum);eligible=[k for k,r in momentum.items() if r['eligible']];selected=sorted(eligible,key=lambda k:(-momentum[k]['base']['lower_weekly_excess'],k))[0] if eligible else None
    dump('momentum_selection.json',{'selected':selected,'frozen_before_final':True,'confirmation_evaluated':selected is not None});confirmation={'qualified':False,'state':'not_opened'}
    if selected:
        lookback,top=map(int,selected.split(':'));panel=panel_for(raw,sorted(new));paths=engine.portfolio_replay(panel,context,lookback,top,final);stress=engine.portfolio_replay(panel,context,lookback,top,final,True);r={'base':portfolio_metrics(paths),'stress':portfolio_metrics(stress)};confirmation={'selected':selected,**r,'qualified':portfolio_gate(r,True)};dump('momentum_final_equity.json',paths)
    dump('momentum_confirmation.json',confirmation);print('COMPLETE',flush=True)
if __name__=='__main__':main()
