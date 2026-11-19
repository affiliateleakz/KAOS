"""Preregistered bounded spot/binary research. No network, credentials or orders."""
import argparse,csv,hashlib,importlib.util,itertools,json
from pathlib import Path
import numpy as np
from scipy.stats import binomtest
import backtest_video_strategies as base
from backtest_all_timeframes import aggregate
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'research/kaos_candidate_v1'
spec=importlib.util.spec_from_file_location('kaos_research',OUT/'strategy.py');strategy=importlib.util.module_from_spec(spec);spec.loader.exec_module(strategy)


def dump(name,value):
    (OUT/name).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def summarize(rows,binary=False,adjust=1):
    net=np.array([(.8 if r['outcome']>0 else -1 if r['outcome']<0 else 0) if binary else r['netR'] for r in rows])
    days={};assets={}
    for r,p in zip(rows,net):
        day=int(r['entry'])//86400000;days[day]=days.get(day,0)+float(p);assets[r['asset']]=assets.get(r['asset'],0)+float(p)
    vals=np.array(list(days.values()));lower=None
    if len(vals)>1:
        rng=np.random.default_rng(5519);means=rng.choice(vals,(5000,len(vals)),replace=True).mean(1)
        lower=float(np.quantile(means,.05/adjust if adjust>1 else .025))
    gains=float(net[net>0].sum());loss=-float(net[net<0].sum())
    m={'trades':len(rows),'days':len(days),'net':float(net.sum()),'mean_per_trade':float(net.mean()) if len(net) else None,'profit_factor':gains/loss if loss else None,'lower_day_bootstrap_mean':lower,'asset_net':assets,'daily_net':{base.iso(k*86400000)[:10]:v for k,v in sorted(days.items())},'observed_exit_reasons':{reason:sum(r.get('reason')==reason for r in rows) for reason in ['stop','target','time']} if not binary else {}}
    if binary:
        w=sum(r['outcome']>0 for r in rows);l=sum(r['outcome']<0 for r in rows);n=w+l
        m.update({'wins':w,'losses':l,'ties':len(rows)-n,'win_rate':w/n if n else None,'wilson_lower':base.wilson(w,n),'p80':float(binomtest(w,n,1/1.8,alternative='greater').pvalue) if n else None,'net_payouts':{str(p):w*p-l for p in [.7,.8,.9,.92]}})
    return m


def spot_gate(m,s,benchmarks,confirmation=False):
    return bool(m['trades']>=(100 if confirmation else 200) and m['days']>=(20 if confirmation else 30) and m['profit_factor'] is not None and m['profit_factor']>=1.1 and m['net']>0 and m['lower_day_bootstrap_mean'] is not None and m['lower_day_bootstrap_mean']>0 and sum(v>0 for v in m['asset_net'].values())>=(2 if confirmation else 4) and s['net']>0 and all(b['mean_per_trade'] is not None and m['mean_per_trade']>b['mean_per_trade'] for b in benchmarks.values()))


def binary_gate(m,s):
    return bool(m['wins']+m['losses']>=200 and m['days']>=3 and m['wilson_lower']>1/1.8 and m['p80']<.05/12 and m['lower_day_bootstrap_mean'] is not None and m['lower_day_bootstrap_mean']>0 and s['net']>0 and sum(v>0 for v in m['asset_net'].values())>=2)


def verified_parts(directories):
    parts=[];manifests=[]
    for directory in directories:
        manifest=json.loads((directory/'manifest.json').read_text());manifests.append(manifest)
        for asset,meta in manifest['assets'].items():
            path=directory/meta['file']
            if hashlib.sha256(path.read_bytes()).hexdigest()!=meta['sha256']:raise ValueError('Minute checksum mismatch')
            a=np.load(path,allow_pickle=False)
            if len(a)!=meta['bars'] or np.any(np.diff(a[:,0])<=0):raise ValueError('Invalid ordering/count')
            for seg in np.split(a,np.where(np.diff(a[:,0])!=60000)[0]+1):
                if len(seg):parts.append((asset,seg))
    if len(set(a for a,_ in parts))!=6:raise ValueError('Require six distinct markets')
    return parts,manifests


def spot_eval(prepared,config,bounds,assets=None):
    tf,family,rr=config;rows=[];stress=[];bench={k:[] for k in ['always_long','trend_long']}
    for asset,a,f in prepared[tf]:
        if assets is not None and asset not in assets:continue
        signals=strategy.spot_signals(f,family)
        rows.extend(strategy.spot_replay(asset,a,f,signals,tf,rr,bounds))
        stress.extend(strategy.spot_replay(asset,a,f,signals,tf,rr,bounds,True))
        for name in bench:bench[name].extend(strategy.spot_replay(asset,a,f,strategy.spot_signals(f,name),tf,rr,bounds))
    return rows,{'base':summarize(rows,adjust=12 if assets is None else 1),'combined_stress':summarize(stress),'benchmarks':{k:summarize(v) for k,v in bench.items()}}


def main():
    p=argparse.ArgumentParser();p.add_argument('--minutes',type=Path,nargs=2,required=True);p.add_argument('--po',type=Path,required=True);args=p.parse_args()
    plan=json.loads((OUT/'plan.json').read_text());parts,manifests=verified_parts(args.minutes)
    dump('provenance.json',{'plan_sha256':hashlib.sha256((OUT/'plan.json').read_bytes()).hexdigest(),'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'strategy_sha256':hashlib.sha256((OUT/'strategy.py').read_bytes()).hexdigest(),'aggregator_sha256':hashlib.sha256((ROOT/'scripts/backtest_all_timeframes.py').read_bytes()).hexdigest(),'minute_manifests':manifests,'minute_bars':sum(len(a) for _,a in parts),'executionEnabled':False})
    prepared={tf:[] for tf in [300,900]}
    for asset,a in parts:
        for tf in prepared:
            bars=aggregate(a,tf,60)
            if len(bars)>=250:prepared[tf].append((asset,a,strategy.features(bars)))
    coverage={str(tf):{asset:{'segments':sum(name==asset for name,_,_ in records),'indicator_bars':sum(len(f) for name,_,f in records if name==asset),'ready_bars_validation':sum(int(((f.ts+tf*1000>=base.stamp(plan['crypto']['validation'][0]))&(f.ts+tf*1000<base.stamp(plan['crypto']['validation'][1]))&f.ready).sum()) for name,_,f in records if name==asset)} for asset in plan['crypto']['assets']} for tf,records in prepared.items()}
    dump('coverage.json',coverage)
    validation=tuple(base.stamp(x) for x in plan['crypto']['validation']);results={};configs={}
    for tf,family,rr in itertools.product([300,900],['breakout20','pullback20','trend_cross'],[1.5,2.]):
        key=f'{tf}:{family}:{rr}';configs[key]=(tf,family,rr)
        _,m=spot_eval(prepared,configs[key],validation);m['eligible']=spot_gate(m['base'],m['combined_stress'],m['benchmarks']);results[key]=m
        print('Spot validation',key,m['base']['trades'],round(m['base']['net'],2),'eligible',m['eligible'],flush=True)
    dump('spot_validation.json',results)
    eligible=[k for k,v in results.items() if v['eligible']]
    selected=sorted(eligible,key=lambda k:(-results[k]['base']['lower_day_bootstrap_mean'],k))[0] if eligible else None
    selection={'selected':selected,'eligible_count':len(eligible),'frozen_before_confirmation':True,'confirmation_evaluated':selected is not None,'executionEnabled':False};dump('spot_selection.json',selection)
    confirmation={'state':'not_opened_no_validation_candidate','qualified':False,'executionEnabled':False}
    if selected:
        final=tuple(base.stamp(x) for x in plan['crypto']['confirmation'])
        rows,m=spot_eval(prepared,configs[selected],final,set(plan['crypto']['fresh_asset_series']))
        confirmation={'selected':selected,**m,'qualified':spot_gate(m['base'],m['combined_stress'],m['benchmarks'],True),'executionEnabled':False}
        with (OUT/'spot_confirmation_trades.csv').open('w') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else ['asset'],lineterminator='\n');writer.writeheader();writer.writerows(rows)
    dump('spot_confirmation.json',confirmation)
    # Buy/hold benchmark on validation only, without opening the reserved new-asset final.
    holds={}
    for asset,a in parts:
        x=a[(a[:,0]>=validation[0])&(a[:,0]<validation[1])]
        if len(x):holds[asset]={'net_return':float((x[-1,4]*(1-.0002)*(1-.001))/(x[0,1]*(1+.0002)*(1+.001))-1),'not_risk_matched':True}
    dump('buy_hold_validation.json',holds)
    poparts,pometa=base.load_po(args.po);bounds=tuple(base.stamp(x) for x in plan['pocket_option']['evaluation']);prepared_po={tf:[] for tf in [60,300]}
    for asset,a in poparts:
        # Physically truncate reserved quotes before aggregation or indicators.
        a=a[a[:,0]<bounds[1]]
        if not len(a):continue
        for tf in prepared_po:
            bars=aggregate(a,tf,5)
            if len(bars)>=60:prepared_po[tf].append((asset,a,strategy.features(bars,60)))
    po_results={}
    for tf,family,count in itertools.product([60,300],['breakout20','pullback20','range_reclaim'],[1,3]):
        rows=[];stress=[]
        for asset,a,f in prepared_po[tf]:
            sig=strategy.binary_signals(f,family)
            rows.extend(strategy.binary_replay(asset,a,f,sig,tf,tf*count,bounds))
            stress.extend(strategy.binary_replay(asset,a,f,sig,tf,tf*count,bounds,True))
        b=summarize(rows,True,12);s=summarize(stress,True);key=f'{tf}:{family}:{count}'
        po_results[key]={'base':b,'combined_stress':s,'historical_gate':binary_gate(b,s)}
        print('Binary historical',key,b['trades'],'gate',binary_gate(b,s),flush=True)
    eligible_po=[k for k,v in po_results.items() if v['historical_gate']]
    choice=sorted(eligible_po,key=lambda k:(-po_results[k]['base']['lower_day_bootstrap_mean'],k))[0] if eligible_po else None
    dump('binary_results.json',{'source':pometa,'results':po_results,'historical_selection':choice,'reserved_evaluated':False,'requires_prospective_broker_evidence':True,'executionEnabled':False})
    print('COMPLETE spot selected',selected,'confirmation qualified',confirmation['qualified'],'binary historical selected',choice,flush=True)
if __name__=='__main__':main()
