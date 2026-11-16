"""Bounded, chronological crypto strategy experiment; no live trading integration."""
import argparse,csv,hashlib,json
from pathlib import Path
from datetime import datetime
import numpy as np
import pandas as pd
from xgboost import XGBClassifier
from research_broker_edge import features,FEATURES,metrics

ROOT=Path(__file__).resolve().parents[1]


def timestamp(value):return int(datetime.fromisoformat(value.replace('Z','+00:00')).timestamp()*1000)


def dataset(folder):
    manifest=json.loads((folder/'manifest.json').read_text());parts=[];segment=0
    for asset,info in sorted(manifest['markets'].items()):
        file=folder/info['file'];raw=file.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=info['sha256']:raise ValueError('Dataset checksum mismatch')
        rows=json.loads(raw)['markets'][asset];part=[];last=None
        for row in rows:
            ts=int(row['ts'])
            if last is not None and ts<=last:raise ValueError('Non-increasing candle timestamps')
            if part and ts!=last+5000:parts.append((asset,part));part=[];segment+=1
            if row.get('trades',0)<=0 or row.get('closeTs')!=ts+5000:raise ValueError('Require complete nonempty five-second bars')
            o,h,l,c=(float(row[k]) for k in ('open','high','low','close'))
            if not all(np.isfinite(v) and v>0 for v in (o,h,l,c)) or not l<=min(o,c)<=max(o,c)<=h:raise ValueError('Invalid OHLC')
            part.append((ts,o,h,l,c));last=ts
        if part:parts.append((asset,part))
    f=features(parts)
    # Shift only within a continuous asset segment, never across missing buckets.
    group=f.groupby('segment',sort=False)
    for bars in (1,2,4,5,7,8,13,14):f['open_shift'+str(bars)]=group.o.shift(-bars)
    for z in (1.5,2.):
        previous_z=group.z.shift();previous_high=group.h.shift();previous_low=group.l.shift()
        f['reclaim'+str(z)]=np.where((previous_z<-z)&(f.z>-z)&(f.body>.3)&(f.c>previous_high)&(f.trend.abs()<2),1,np.where((previous_z>z)&(f.z<z)&(f.body<-.3)&(f.c<previous_low)&(f.trend.abs()<2),-1,0))
    return f,manifest


def replay(f,side,expiry,start,end,delay=0,adverse_bps=0):
    decision=f.decision.to_numpy();entry=f['open_shift'+str(1+delay)].to_numpy();exit=f['open_shift'+str(1+delay+expiry//5)].to_numpy()
    mask=(side!=0)&(decision>=start)&(decision+(delay*5+expiry)*1000<end)&np.isfinite(entry)&np.isfinite(exit)
    rows=[];busy={};assets=f.asset.to_numpy();segments=f.segment.to_numpy()
    for i in np.flatnonzero(mask):
        asset=assets[i]
        if decision[i]<busy.get(asset,0):continue
        fill=entry[i]*(1+side[i]*adverse_bps/10000);move=(exit[i]-fill)*side[i];outcome=0 if move==0 else 1 if move>0 else -1
        ts=int(decision[i]+delay*5000);settle=ts+expiry*1000
        rows.append({'asset':asset,'segment':int(segments[i]),'entry_ts':ts,'exit_ts':settle,'direction':'BUY' if side[i]>0 else 'SELL','entry':float(fill),'settlement':float(exit[i]),'outcome':outcome,'utc_day':datetime.fromtimestamp(ts/1000,__import__('datetime').timezone.utc).strftime('%Y-%m-%d')})
        busy[asset]=settle
    return rows


def eligible(m):
    return m['decided']>=200 and m['days']>=2 and len(m['by_asset'])>=2 and all(p>0 for p in m['daily_pnl'].values())


def write(path,data):path.write_text(json.dumps(data,indent=2)+'\n')


def main():
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    plan_path=ROOT/'research/crypto_strategy_v1/plan.json';plan=json.loads(plan_path.read_text());cut1=timestamp(plan['development_end_utc']);cut2=timestamp(plan['validation_end_utc']);end=timestamp(plan['test_end_utc'])
    args.out.mkdir(parents=True,exist_ok=True);f,manifest=dataset(args.data)
    write(args.out/'provenance.json',{'plan_sha256':hashlib.sha256(plan_path.read_bytes()).hexdigest(),'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'source_manifest_sha256':hashlib.sha256((args.data/'manifest.json').read_bytes()).hexdigest(),'markets':manifest['markets'],'feature_rows':len(f),'warmup_bars':300,'live_approved':False})
    candidates=[]
    rule_cols=['momentum','pullback','breakout']+['fade'+str(z) for z in (1.5,2.,2.5)]+['streak'+str(n) for n in (3,4,5)]+['reclaim'+str(z) for z in (1.5,2.)]
    for col in rule_cols:
        for expiry in (15,30,60):candidates.append((col+'_'+str(expiry),f[col].to_numpy(),expiry,None))
    for expiry in (15,30,60):
        target=f['open_shift'+str(1+expiry//5)];entry=f.open_shift1
        mask=(f.decision+expiry*1000<cut1)&target.notna()&(target!=entry)
        chosen=[];last={}
        for i in np.flatnonzero(mask):
            row=f.iloc[i]
            if row.decision>=last.get(row.asset,0):chosen.append(i);last[row.asset]=row.decision+expiry*1000
        train=f.iloc[chosen];y=(target.iloc[chosen]>entry.iloc[chosen]).astype(int)
        model=XGBClassifier(n_estimators=80,max_depth=2,learning_rate=.03,min_child_weight=20,reg_lambda=20,n_jobs=1,random_state=47,tree_method='hist',objective='binary:logistic')
        model.fit(train[FEATURES],y);prob=model.predict_proba(f[FEATURES])[:,1]
        for confidence in (.55,.6,.65):candidates.append((f'xgb_{expiry}_{confidence}',np.where(prob>=confidence,1,np.where(prob<=1-confidence,-1,0)),expiry,model))
    assert len(candidates)==plan['maximum_candidates']
    validation=[]
    for name,side,expiry,_ in candidates:
        m=metrics(replay(f,side,expiry,cut1,cut2),len(candidates));validation.append({'candidate':name,'expiry':expiry,'eligible':eligible(m),**m})
    write(args.out/'validation.json',validation)
    valid=[m for m in validation if m['eligible']];selected=max(valid,key=lambda m:m['wilson_lower_95']) if valid else None
    choice={'selected':selected['candidate'] if selected else None,'eligible_candidates':len(valid),'selection_rule':plan['selection'],'trials':len(candidates),'frozen_before_final_evaluation':True}
    write(args.out/'selection.json',choice);print(json.dumps(choice),flush=True)
    result={'state':'no_validation_candidate','selected':None,'final':None,'live_approved':False,'validation_days':2,'final_days':2,'limitations':['Only one week and three correlated crypto assets.','Proxy binary outcomes, assumed payouts, no broker execution verification.','Any positive result requires new prospective demo validation.']}
    if selected:
        name,side,expiry,model=next(c for c in candidates if c[0]==selected['candidate'])
        held=replay(f,side,expiry,cut2,end);m=metrics(held)
        delayed=metrics(replay(f,side,expiry,cut2,end,delay=1));slipped=metrics(replay(f,side,expiry,cut2,end,adverse_bps=1))
        passed=eligible(m) and m['wilson_lower_95']>1/1.8 and selected['bonferroni_pvalue']<.05 and delayed['pnl_at_payout']['0.8']>0 and slipped['pnl_at_payout']['0.8']>0
        result.update(state='research_candidate_needs_forward_validation' if passed else 'failed_final_gate',selected=name,final=m,delayed_entry=delayed,adverse_entry_1bp=slipped,validation_adjusted_pvalue=selected['bonferroni_pvalue'])
        if model is not None:model.save_model(args.out/'selected_model.json')
        with (args.out/'final_trades.csv').open('w') as handle:
            writer=csv.DictWriter(handle,fieldnames=list(held[0]) if held else ['asset'],lineterminator='\n');writer.writeheader();writer.writerows(held)
    write(args.out/'result.json',result);print(json.dumps(result),flush=True)

if __name__=='__main__':main()
