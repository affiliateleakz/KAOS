"""Longer-horizon research engines. No broker or order API."""
import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd
P=Path(__file__).resolve().parents[1]/'kaos_candidate_v1/strategy.py'
spec=importlib.util.spec_from_file_location('previous_research',P);prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)


def swing_features(bars):
    f=prior.features(bars);f['highclose20']=f.close.rolling(20).max();f['low10']=f.low.shift().rolling(10).min();return f


def swing_replay(asset,a,f,tf,family,mult,bounds,stress=False):
    signals=prior.spot_signals(f,family);rows=[];available=0;first=int(a[0,0]);delay=3600000 if stress else 0;fee=.002 if stress else .001;slip=.0004 if stress else .0002
    decision_to_row={int(ts)+tf*1000:i for i,ts in enumerate(f.ts)}
    for i in np.flatnonzero(signals):
        decision=int(f.ts.iloc[i])+tf*1000;entry=decision+delay;deadline=entry+7*86400000
        if decision<bounds[0] or deadline>=bounds[1]:continue
        ei=(entry-first)//3600000;end=(deadline-first)//3600000
        if ei<available or ei<1 or end>=len(a):continue
        if a[ei,0]!=entry or a[end,0]!=deadline:raise ValueError('Unobserved entry')
        raw=float(a[ei,1]);risk=mult*float(f.atr.iloc[i])
        if risk<.01*raw or risk>=raw:continue
        stop=raw-risk;pending=False;xi=end;price=float(a[end,1]);reason='time'
        for j in range(ei,end):
            ts,o,h,l,c=a[j]
            if o<=stop:xi=j;price=float(o);reason='gap_stop';break
            if pending:xi=j;price=float(o);reason='signal_exit';break
            if l<=stop:xi=j;price=stop;reason='stop';break
            ri=decision_to_row.get(int(ts)+3600000)
            if ri is not None:
                r=f.iloc[ri];stop=max(stop,float(r.highclose20-mult*r.atr))
                pending=bool(r.close<r.ema50 or r.close<r.low10)
        paid=raw*(1+slip);received=price*(1-slip);net=(received-paid-fee*(paid+received))/risk
        rows.append({'asset':asset,'entry':entry,'exit':int(a[xi,0]),'entry_price':paid,'exit_price':received,'risk':risk,'netR':net,'reason':reason,'executionEnabled':False});available=xi+1
    return rows


def rebalance(cash,q,prices,weights,cost):
    """Self-financing fractional spot positions, including turnover costs."""
    q=q.copy();equity=float(cash+q@prices);delta=equity*weights-q*prices
    sell=np.maximum(-delta,0);q-=sell/prices;cash+=float(sell.sum()*(1-cost))
    buys=np.maximum(delta,0);needed=float(buys.sum()*(1+cost));scale=min(1.,cash/needed) if needed else 0.
    q+=buys*scale/prices;cash-=needed*scale
    if cash< -1e-9 or np.any(q< -1e-9):raise ValueError('Negative cash or holdings')
    return max(cash,0.),np.maximum(q,0.)


def daily_context(parts,aggregate):
    context={}
    for asset,a in parts:
        bars=aggregate(a,86400,3600)
        if len(bars)<250:continue
        f=prior.features(bars)
        for n in (20,60):f['mom'+str(n)]=f.close/f.close.shift(n)-1
        for r in f.itertuples():
            if r.ready:context[(asset,int(r.ts))]=(float(r.close),float(r.ema200),float(r.mom20),float(r.mom60))
    return context


def portfolio_replay(panel,context,lookback,top,bounds,stress=False):
    assets,times,opens,closes=panel;mask=(times>=bounds[0])&(times<bounds[1]);ts=times[mask];op=opens[mask];cp=closes[mask]
    if not len(ts):return {'strategy':[],'matched':[],'passive':[],'times':[]}
    cost=.0024 if stress else .0012;delay=3600000 if stress else 0
    state={key:(1.,np.zeros(len(assets))) for key in ['strategy','matched','passive']};equities={k:[] for k in state};gap_liquidations=0
    for i,t in enumerate(ts):
        if i and t!=ts[i-1]+3600000:
            for key,(cash,q) in state.items():state[key]=(float(cash+q@op[i]*(1-cost)),np.zeros(len(assets)))
            gap_liquidations+=1
        monday=((int(t)-delay)//86400000+3)%7==0
        rebalance_time=(int(t)-delay)%86400000==0 and monday
        if rebalance_time:
            day=(int(t)-delay)//86400000*86400000;rank=[]
            for j,asset in enumerate(assets):
                r=context.get((asset,day-86400000))
                if r is not None and r[0]>r[1] and r[2 if lookback==20 else 3]>0:rank.append((r[2 if lookback==20 else 3],asset,j))
            ranked=sorted(rank,key=lambda r:(-r[0],r[1]))[:top];weights=np.zeros(len(assets))
            for _,_,j in ranked:weights[j]=1/top
            targets={'strategy':weights,'matched':np.full(len(assets),weights.sum()/len(assets)),'passive':np.full(len(assets),1/len(assets))}
            for key in state:state[key]=rebalance(*state[key],op[i],targets[key],cost)
        for key,(cash,q) in state.items():equities[key].append(float(cash+q@cp[i]))
    for key,(cash,q) in state.items():equities[key][-1]=float(cash+q@cp[-1]*(1-cost))
    return {**equities,'times':ts.tolist(),'gap_liquidations':gap_liquidations,'executionEnabled':False}
