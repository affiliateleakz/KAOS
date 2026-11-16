"""Offline bounded strategy research. Never imports a backup model or places orders."""
import argparse,csv,hashlib,json,math,zipfile
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import binomtest
from xgboost import XGBClassifier


def date(ts):return datetime.fromtimestamp(ts/1000,timezone.utc).isoformat()


def wilson(w,n):
    if not n:return 0.
    z=1.96;p=w/n
    return (p+z*z/(2*n)-z*math.sqrt(p*(1-p)/n+z*z/(4*n*n)))/(1+z*z/n)


def load(path):
    raw=path.read_bytes();archive=zipfile.ZipFile(path)
    members=[i for i in archive.infolist() if i.filename.endswith('.json') and i.file_size<150_000_000]
    if len(members)!=1:raise ValueError('Expected one bounded JSON backup')
    data=json.loads(archive.read(members[0]));markets=data['rawCandleHistory']['byAsset'];quality=Counter();parts=[]
    for asset,rows in sorted(markets.items()):
        clean={};conflict=set()
        for row in rows:
            quality['raw_bars']+=1
            try:
                ts=int(row['ts']);o,h,l,c=[float(row[k]) for k in ('open','high','low','close')]
                if ts<=0 or ts%5000 or not all(math.isfinite(v) and v>0 for v in (o,h,l,c)) or not l<=min(o,c)<=max(o,c)<=h:raise ValueError()
                value=(ts,o,h,l,c)
                if ts in clean:
                    quality['duplicate_bars']+=1
                    if clean[ts]!=value:conflict.add(ts)
                clean[ts]=value
                quality['close_marker_'+str(int(row.get('closeTs',ts))-ts)]+=1
                if h==l:quality['flat_bars']+=1
            except (ValueError,TypeError,KeyError,OverflowError):quality['invalid_bars']+=1
        for ts in conflict:clean.pop(ts,None)
        quality['conflicting_timestamps']+=len(conflict)
        ordered=sorted(clean.values());segment=[]
        for row in ordered:
            if segment and row[0]!=segment[-1][0]+5000:
                parts.append((asset,segment));segment=[];quality['gaps']+=1
            segment.append(row)
        if segment:parts.append((asset,segment))
    quality.update(markets=len(markets),segments=len(parts),valid_bars=sum(len(r) for _,r in parts))
    result=dict(quality)
    records=data.get('popupData',{}).get('tradeRecords',[]);audit=Counter()
    for record in records:
        audit['records']+=1;audit['reported_'+str(record.get('result'))]+=1
        audit['broker_flagged' if record.get('__brokerConfirmed') else 'not_broker_flagged']+=1
        try:
            direction=record['direction']
            if direction not in ('BUY','SELL'):raise ValueError()
            change=(float(record['exitPrice'])-float(record['entryPrice']))*(1 if direction=='BUY' else -1)
            if not math.isfinite(change):raise ValueError()
            expected='draw' if change==0 else 'win' if change>0 else 'loss'
            audit['price_outcome_agrees' if expected==record.get('result') else 'price_outcome_mismatch']+=1
        except (KeyError,ValueError,TypeError):audit['uncheckable']+=1
    result['recorded_trade_audit']=dict(audit)
    return parts,result,hashlib.sha256(raw).hexdigest()


def features(parts):
    frames=[]
    for segment,(asset,rows) in enumerate(parts):
        if len(rows)<320:continue
        f=pd.DataFrame(rows,columns=['ts','o','h','l','c']);c=f.c;o=f.o;span=(f.h-f.l).clip(lower=1e-12)
        tr=pd.concat([span,(f.h-c.shift()).abs(),(f.l-c.shift()).abs()],axis=1).max(axis=1)
        atr=tr.rolling(20).mean().clip(lower=1e-12)
        e20=c.ewm(span=20,adjust=False).mean();e50=c.ewm(span=50,adjust=False).mean();sd=c.rolling(20).std().clip(lower=1e-12)
        f['body']=(c-o)/span;f['lower']=(pd.concat([o,c],axis=1).min(axis=1)-f.l)/span;f['upper']=(f.h-pd.concat([o,c],axis=1).max(axis=1))/span
        f['trend']=(e20-e50)/atr;f['z']=(c-c.rolling(20).mean())/sd
        f['distance']=(c-e20)/atr;f['volatility']=atr/tr.rolling(100).mean().clip(lower=1e-12)
        for lag in (1,3,6,12):f['return'+str(lag)]=(c-c.shift(lag))/atr
        f['range']=span/atr
        f['momentum']=np.where((f.body>=.6)&(f.trend>.3),1,np.where((f.body<=-.6)&(f.trend<-.3),-1,0))
        f['pullback']=np.where((f.trend>.3)&(c.shift()<o.shift())&(f.body>.5)&(c>f.h.shift()),1,np.where((f.trend<-.3)&(c.shift()>o.shift())&(f.body<-.5)&(c<f.l.shift()),-1,0))
        f['breakout']=np.where((c>f.h.shift().rolling(20).max())&(f.body>.5),1,np.where((c<f.l.shift().rolling(20).min())&(f.body<-.5),-1,0))
        for z in (1.5,2.,2.5):f['fade'+str(z)]=np.where((f.z<-z)&(f.lower>.3),1,np.where((f.z>z)&(f.upper>.3),-1,0))
        for streak in (3,4,5):
            color=np.sign(c-o);total=color.rolling(streak).sum();f['streak'+str(streak)]=np.where(total==streak,-1,np.where(total==-streak,1,0))
        for expiry in (15,30,60):
            f['entry']=o.shift(-1);f['exit'+str(expiry)]=o.shift(-1-expiry//5)
        f['segment']=segment;f['asset']=asset;f['decision']=f.ts+5000
        # 300 prior completed bars; missing next/settlement bars remain NaN, never forward-filled.
        frames.append(f.iloc[299:])
    if not frames:raise ValueError('No adequately long contiguous segments')
    return pd.concat(frames,ignore_index=True).sort_values(['decision','asset']).reset_index(drop=True)


FEATURES=['body','lower','upper','trend','z','distance','volatility','return1','return3','return6','return12','range']


def trades(f,side,expiry,start,end):
    result=[];busy={}
    for i in np.flatnonzero((side!=0)&(f.decision.to_numpy()>=start)&(f.decision.to_numpy()+expiry*1000<end)):
        row=f.iloc[i]
        price=row['exit'+str(expiry)]
        if not math.isfinite(price) or row.decision<busy.get(row.asset,0):continue
        move=price-row.entry;s=int(side[i]);outcome=0 if move==0 else 1 if move*s>0 else -1
        result.append({'asset':row.asset,'segment':int(row.segment),'entry_ts':int(row.decision),'exit_ts':int(row.decision+expiry*1000),'direction':'BUY' if s==1 else 'SELL','entry':row.entry,'settlement':price,'outcome':outcome,'utc_day':date(row.decision)[:10]})
        busy[row.asset]=row.decision+expiry*1000
    return result


def metrics(rows,trials=1):
    w=sum(r['outcome']==1 for r in rows);l=sum(r['outcome']==-1 for r in rows);n=w+l;daily={};assets={}
    for r in rows:
        pnl=.8 if r['outcome']==1 else -1 if r['outcome']==-1 else 0
        daily[r['utc_day']]=daily.get(r['utc_day'],0)+pnl
        a=assets.setdefault(r['asset'],{'wins':0,'losses':0,'pnl':0});a['wins']+=r['outcome']==1;a['losses']+=r['outcome']==-1;a['pnl']+=pnl
    vals=np.array(list(daily.values()));lower=None
    if len(vals)>=3:
        rng=np.random.default_rng(47);lower=float(np.quantile(rng.choice(vals,size=(5000,len(vals)),replace=True).sum(axis=1),.025))
    return {'trades':len(rows),'decided':n,'wins':w,'losses':l,'ties':len(rows)-n,'win_rate':w/n if n else None,'wilson_lower_95':wilson(w,n),'break_even_payout':l/w if w else None,'pnl_at_payout':{str(p):round(w*p-l,5) for p in (.7,.8,.9)},'days':len(daily),'daily_pnl':daily,'daily_cluster_bootstrap_lower_pnl95':lower,'binomial_pvalue_at_80pct':float(binomtest(w,n,1/1.8,alternative='greater').pvalue) if n else 1.,'bonferroni_pvalue':min(1.,float(binomtest(w,n,1/1.8,alternative='greater').pvalue)*trials) if n else 1.,'by_asset':assets}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('archive',type=Path);parser.add_argument('--out',type=Path,required=True);parser.add_argument('--baseline-input',type=Path);args=parser.parse_args()
    parts,quality,digest=load(args.archive);f=features(parts);timeline=np.unique(f.decision);cut1=int(timeline[int(len(timeline)*.6)]);cut2=int(timeline[int(len(timeline)*.8)]);end=int(timeline[-1]+1)
    args.out.mkdir(parents=True,exist_ok=True)
    if args.baseline_input:
        archive=zipfile.ZipFile(args.archive);member=next(i for i in archive.infolist() if i.filename.endswith('.json'))
        raw=json.loads(archive.read(member))['rawCandleHistory']['byAsset']
        markers={asset:{str(r['ts']):r.get('closeTs',r['ts']) for r in rows} for asset,rows in raw.items()}
        args.baseline_input.write_text(json.dumps({'parts':[(asset,rows) for asset,rows in parts if len(rows)>=320],'markers':markers,'start':cut1,'end':cut2}))
    plan=Path(__file__).resolve().parents[1]/'research/pocket_option_20261008/plan.json'
    provenance={'archive_sha256':digest,'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'plan_sha256':hashlib.sha256(plan.read_bytes()).hexdigest(),'quality':quality,'eligible_feature_rows':len(f),'development_start':date(timeline[0]),'validation_start':date(cut1),'final_start':date(cut2),'end':date(end),'execution_approved':False}
    (args.out/'data_audit.json').write_text(json.dumps(provenance,indent=2)+'\n');print(json.dumps(provenance),flush=True)
    candidates=[]
    for col in ['momentum','pullback','breakout']+['fade'+str(z) for z in (1.5,2.,2.5)]+['streak'+str(n) for n in (3,4,5)]:
        for expiry in (15,30,60):candidates.append((col+'_'+str(expiry),f[col].to_numpy(),expiry))
    for expiry in (15,30,60):
        valid=(f.decision+expiry*1000<cut1)&f['exit'+str(expiry)].notna()&(f['exit'+str(expiry)]!=f.entry)
        # Throttle training observations by market to reduce overlapping labels.
        train=f[valid].copy();last={};chosen=[]
        for i,row in train.iterrows():
            if row.decision>=last.get(row.asset,0):chosen.append(i);last[row.asset]=row.decision+expiry*1000
        train=f.loc[chosen]
        y=(train['exit'+str(expiry)]>train.entry).astype(int)
        model=XGBClassifier(n_estimators=80,max_depth=2,learning_rate=.03,min_child_weight=20,reg_lambda=20,n_jobs=1,random_state=47,tree_method='hist',objective='binary:logistic')
        model.fit(train[FEATURES],y);prob=model.predict_proba(f[FEATURES])[:,1]
        for confidence in (.6,.65,.7):
            side=np.where(prob>=confidence,1,np.where(prob<=1-confidence,-1,0));candidates.append((f'xgb_{expiry}_{confidence}',side,expiry))
    val=[]
    for name,side,expiry in candidates:
        m=metrics(trades(f,side,expiry,cut1,cut2),len(candidates));val.append({'candidate':name,'expiry':expiry,**m})
    (args.out/'validation.json').write_text(json.dumps(val,indent=2)+'\n')
    eligible=[v for v in val if v['decided']>=200 and v['days']>=3 and v['pnl_at_payout']['0.8']>0]
    selected=max(eligible,key=lambda v:v['wilson_lower_95']) if eligible else None
    # Selection is written before the final period is evaluated. Do not select using final results.
    (args.out/'selection.json').write_text(json.dumps({'trials':len(candidates),'selected':selected['candidate'] if selected else None,'reason':'highest eligible validation Wilson lower bound' if selected else 'No candidate passed validation eligibility'},indent=2)+'\n')
    result={'selection':selected['candidate'] if selected else None,'trials':len(candidates),'live_approved':False,'state':'no_validation_candidate','final':None}
    if selected:
        name,side,expiry=next(c for c in candidates if c[0]==selected['candidate']);held=trades(f,side,expiry,cut2,end);m=metrics(held)
        passed=m['decided']>=200 and m['days']>=3 and m['wilson_lower_95']>1/1.8 and (m['daily_cluster_bootstrap_lower_pnl95'] or -1)>0
        result.update(state='historical_candidate_only' if passed else 'failed_final_gate',final=m)
        with (args.out/'final_trades.csv').open('w') as handle:
            writer=csv.DictWriter(handle,fieldnames=list(held[0]) if held else ['asset'],lineterminator='\n');writer.writeheader();writer.writerows(held)
    (args.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)

if __name__=='__main__':main()
