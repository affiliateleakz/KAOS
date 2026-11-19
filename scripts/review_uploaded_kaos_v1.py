"""Offline numerical audit of hash-pinned reviewed calculation files only."""
import argparse,hashlib,importlib.util,json,sys,csv
from pathlib import Path
import numpy as np
import pandas as pd
from backtest_all_timeframes import aggregate
import backtest_video_strategies as base
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'research/uploaded_kaos_v1_review'
HASHES={'strategy.py':'11a6b7c4c8eb34fe196f47408ba9e5ffd9acfaed2b24e6a8dec4028f64eec69f','backtest.py':'593e449cffc197730252ef3c9467baa76a07a298c49f02c6a1d6ee7e3b134cd8'}

def pure_modules(path):
    for name,digest in HASHES.items():
        if hashlib.sha256((path/name).read_bytes()).hexdigest()!=digest:raise ValueError('Unreviewed calculation source: '+name)
    modules=[];old=sys.modules.get('strategy')
    try:
        for name in ['strategy','backtest']:
            alias='_reviewed_upload_'+name;spec=importlib.util.spec_from_file_location(alias,path/(name+'.py'));m=importlib.util.module_from_spec(spec);sys.modules[alias]=m
            if name=='backtest':sys.modules['strategy']=modules[0]
            spec.loader.exec_module(m);modules.append(m)
    finally:
        if old is None:sys.modules.pop('strategy',None)
        else:sys.modules['strategy']=old
    return modules


def correct_wr_interval(outcomes):
    values=np.array([1 if x in ['tp','tp_gap'] else 0 for x in outcomes if x in ['tp','tp_gap','sl','sl_gap']])
    if len(values)<10:return None
    rng=np.random.default_rng(7);means=rng.choice(values,(2000,len(values)),replace=True).mean(1)
    return [float(np.quantile(means,.025)),float(np.quantile(means,.975))]


def encoded_audit(strategy,backtest):
    trades=pd.DataFrame({'outcome':['tp','sl']*10,'pnl_atr':[3.,-5.]*10});df=pd.DataFrame({'ts':np.arange(40),'open':100.,'high':104.,'low':99.,'close':103.});atr=np.r_[np.ones(60),np.full(40,10.)]
    wrong=backtest.simulate_entries(df,[(0,1)],atr,3,5,24,.02).iloc[0];right=backtest.simulate_entries(df,[(0,1)],atr[60:],3,5,24,.02).iloc[0]
    return {'balanced_sample_actual_win_rate':.5,'source_bootstrap_interval':list(backtest.bootstrap_wr(trades)),'corrected_iid_bootstrap_interval':correct_wr_interval(trades.outcome),'wrong_test_atr':float(wrong.atr),'aligned_test_atr':float(right.atr),'wrong_outcome':wrong.outcome,'aligned_outcome':right.outcome,'note':'Synthetic regression demonstration, not trading evidence.'}


def totals(rows,cost):
    pnl=np.array([r[cost] for r in rows]);gain=float(pnl[pnl>0].sum());loss=-float(pnl[pnl<0].sum());wins=sum(r['outcome'] in ['tp','tp_gap'] for r in rows);losses=sum(r['outcome'] in ['sl','sl_gap'] for r in rows)
    return {'trades':len(rows),'barrier_wins':wins,'barrier_losses':losses,'time_exits':len(rows)-wins-losses,'barrier_win_rate':wins/(wins+losses) if wins+losses else None,'net_profitable_trade_rate':float((pnl>0).mean()) if len(pnl) else None,'net_ATR':float(pnl.sum()),'mean_ATR':float(pnl.mean()) if len(pnl) else None,'profit_factor':gain/loss if loss else None}


def price_cost_pnl(side,entry,exit,atr,fee,slip):
    paid=entry*(1+side*slip);received=exit*(1-side*slip)
    return (side*(received-paid)-fee*(abs(paid)+abs(received)))/atr


def main():
    p=argparse.ArgumentParser();p.add_argument('--package',type=Path,required=True);p.add_argument('--minutes',type=Path,required=True);a=p.parse_args();strategy,backtest=pure_modules(a.package);plan=json.loads((OUT/'plan.json').read_text());manifest=json.loads((a.minutes/'manifest.json').read_text());bounds=tuple(base.stamp(x) for x in plan['diagnostic']['evaluation']);rows=[]
    proof=encoded_audit(strategy,backtest);(OUT/'regressions.json').write_text(json.dumps(proof,indent=2)+'\n')
    ledger=pd.read_csv(a.package/'out/pooled_trades.csv').sort_values('exit_ts').reset_index(drop=True);m=backtest.metrics(ledger,3,5);ledger_review={'metrics':{k:float(v) if isinstance(v,(np.floating,np.integer)) else v for k,v in m.items()},'source_confidence':list(backtest.bootstrap_wr(ledger)),'corrected_iid_interval_not_clustered':correct_wr_interval(ledger.outcome),'source_raw_candle_files_included':len(list((a.package/'data').glob('*.csv'))),'classifications':pd.read_csv(a.package/'out/portability.csv').loc[lambda f:f.asset=='USDJPY',['asset','tf','class']].to_dict('records')};(OUT/'ledger_review.json').write_text(json.dumps(ledger_review,indent=2,allow_nan=False)+'\n')
    for asset in plan['diagnostic']['markets']:
        meta=manifest['assets'][asset];path=a.minutes/meta['file']
        if hashlib.sha256(path.read_bytes()).hexdigest()!=meta['sha256']:raise ValueError('Minute checksum mismatch')
        data=np.load(path,allow_pickle=False)
        for seg in np.split(data,np.where(np.diff(data[:,0])!=60000)[0]+1):
            if not len(seg):continue
            bars=aggregate(seg,300,60)
            if len(bars)<85:continue
            frame=pd.DataFrame(bars,columns=['ts','open','high','low','close']);ind=strategy.indicators(frame,strategy.DEFAULT);signals=strategy.signal_series(ind,strategy.DEFAULT);atr=ind.atr.to_numpy();signals[:60]=0
            entries=[]
            for i in np.flatnonzero(signals):
                decision=int(bars[i,0])+300000;deadline=decision+24*300000
                if decision>=bounds[0] and deadline<bounds[1] and i+25<len(frame) and np.isfinite(atr[i]) and bars[i+1,1]>5*atr[i]:entries.append((int(i),int(signals[i])))
            for mode in ['hypothetical_long_and_short','long_only_spot']:
                selected=entries if mode.startswith('hypothetical') else [(i,s) for i,s in entries if s>0]
                # Full frame and full ATR share their original index, avoiding package split bug.
                trades=backtest.simulate_entries(frame,selected,atr,3,5,24,0)
                for r in trades.itertuples():
                    exit_price=float(r.exit)
                    if r.outcome=='tp_gap':exit_price=float(r.entry)+int(r.side)*3*float(r.atr)
                    gross=int(r.side)*(exit_price-float(r.entry))/float(r.atr)
                    rows.append({'asset':asset,'mode':mode,'entry_ts':int(r.entry_ts),'exit_bar_ts':int(r.exit_ts),'side':int(r.side),'entry':float(r.entry),'exit':exit_price,'atr':float(r.atr),'outcome':r.outcome,'net_ATR_source_cost':gross-.04,'net_ATR_price_cost':price_cost_pnl(int(r.side),float(r.entry),exit_price,float(r.atr),.001,.0002),'net_ATR_double_cost':price_cost_pnl(int(r.side),float(r.entry),exit_price,float(r.atr),.002,.0004),'executionEnabled':False})
    report={'scope':'Reused historical prices, corrected diagnostic only; not original42pair reproduction, not OOS or prospective. Short financing unavailable. No binary expiry result.','plan_sha256':hashlib.sha256((OUT/'plan.json').read_bytes()).hexdigest(),'source_hashes':HASHES,'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'sources':manifest,'results':{}}
    for mode in ['hypothetical_long_and_short','long_only_spot']:
        selected=[r for r in rows if r['mode']==mode];report['results'][mode]={cost:totals(selected,cost) for cost in ['net_ATR_source_cost','net_ATR_price_cost','net_ATR_double_cost']};report['results'][mode]['by_asset']={asset:totals([r for r in selected if r['asset']==asset],'net_ATR_price_cost') for asset in plan['diagnostic']['markets']}
    (OUT/'diagnostic.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    with (OUT/'diagnostic_trades.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else ['asset'],lineterminator='\n');w.writeheader();w.writerows(rows)
    print(json.dumps(report['results'],indent=2),flush=True)
if __name__=='__main__':main()
