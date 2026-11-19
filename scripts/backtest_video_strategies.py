"""Frozen video-derived binary-price replay. No real orders or profitability guarantees."""
import argparse,csv,hashlib,json,math
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
from statistics import NormalDist
import numpy as np
import pandas as pd
from scipy.stats import binomtest

ROOT=Path(__file__).resolve().parents[1]
VARIANTS={'macd_rsi':['strict','recent2'],'ma_macd_rsi':['ema5_20','ema10_20','sma5_20'],'sar_supertrend':['10_3','7_3','10_2','14_3']}


def stamp(s):return int(pd.Timestamp(s,tz='UTC').timestamp()*1000)
def iso(ts):return datetime.fromtimestamp(ts/1000,timezone.utc).isoformat()
def config_id(c):return f"{c['family']}:{c['variant']}:{c['tf']}s:{c['expiry']}s"


def split_parts(asset,rows):
    clean={};conflict=set()
    for row in rows:
        try:
            ts=int(row['ts']);values=tuple(float(row[k]) for k in ('open','high','low','close'))
            if ts%5000 or not all(math.isfinite(v) and v>0 for v in values) or not values[2]<=min(values[0],values[3])<=max(values[0],values[3])<=values[1]:continue
            if ts in clean and clean[ts]!=values:conflict.add(ts)
            clean[ts]=values
        except (KeyError,ValueError,TypeError):continue
    for ts in conflict:clean.pop(ts,None)
    parts=[];segment=[]
    for ts,values in sorted(clean.items()):
        if segment and ts!=segment[-1][0]+5000:parts.append((asset,np.array(segment,dtype=float)));segment=[]
        segment.append((ts,*values))
    if segment:parts.append((asset,np.array(segment,dtype=float)))
    return parts


def load_proxy(path):
    manifest=json.loads((path/'manifest.json').read_text());parts=[]
    for asset,meta in manifest['markets'].items():
        file=path/meta['file'];raw=file.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=meta['sha256']:raise ValueError('Proxy checksum mismatch')
        parts+=split_parts(asset,json.loads(raw)['markets'][asset])
    return parts,manifest


def load_po(path):
    import zipfile
    with zipfile.ZipFile(path) as archive:
        names=[i for i in archive.infolist() if i.filename.endswith('.json') and i.file_size<150_000_000]
        if len(names)!=1:raise ValueError('Expected a bounded candle export')
        data=json.loads(archive.read(names[0]))
    parts=[]
    for asset,rows in data['rawCandleHistory']['byAsset'].items():parts+=split_parts(asset,rows)
    return parts,{'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'markets':len(data['rawCandleHistory']['byAsset']),'bars':sum(len(p) for _,p in parts),'segments':len(parts)}


def aggregate(a,tf):
    n=tf//5;start=int((-int(a[0,0])//5000)%n);trim=a[start:];trim=trim[:len(trim)//n*n]
    if not len(trim):return np.empty((0,5))
    x=trim.reshape(-1,n,5)
    return np.column_stack((x[:,0,0],x[:,0,1],x[:,:,2].max(axis=1),x[:,:,3].min(axis=1),x[:,-1,4]))


def rma(x,n):
    out=np.full(len(x),np.nan);valid=np.flatnonzero(np.isfinite(x))
    if len(valid)<n:return out
    i=valid[n-1];out[i]=np.mean(x[valid[:n]])
    for j in range(i+1,len(x)):out[j]=out[j-1] if not math.isfinite(x[j]) else (out[j-1]*(n-1)+x[j])/n
    return out


def ema(x,n):return pd.Series(x).ewm(span=n,adjust=False).mean().to_numpy()
def cross(x,y):return np.r_[False,(x[1:]>y[1:])&(x[:-1]<=y[:-1])]


def rsi(x,n):
    d=np.r_[np.nan,np.diff(x)];up=rma(np.maximum(d,0),n);down=rma(np.maximum(-d,0),n)
    with np.errstate(divide='ignore',invalid='ignore'):out=100-100/(1+up/down)
    out[(up==0)&(down==0)]=50;out[(up>0)&(down==0)]=100
    return out


def sar(high,low,close):
    out=np.full(len(close),np.nan)
    if len(close)<2:return out
    rising=close[1]>close[0];value=low[0] if rising else high[0];extreme=high[1] if rising else low[1];af=.02
    out[1]=value
    for i in range(2,len(close)):
        value+=af*(extreme-value)
        if rising:
            value=min(value,low[i-1],low[i-2])
            if low[i]<value:rising=False;value=extreme;extreme=low[i];af=.02
            elif high[i]>extreme:extreme=high[i];af=min(.2,af+.02)
        else:
            value=max(value,high[i-1],high[i-2])
            if high[i]>value:rising=True;value=extreme;extreme=high[i];af=.02
            elif low[i]<extreme:extreme=low[i];af=min(.2,af+.02)
        out[i]=value
    return out


def supertrend(high,low,close,period,mult):
    tr=np.maximum(high-low,np.maximum(np.abs(high-np.r_[close[0],close[:-1]]),np.abs(low-np.r_[close[0],close[:-1]])))
    atr=rma(tr,period);upper=(high+low)/2+mult*atr;lower=(high+low)/2-mult*atr;direction=np.zeros(len(close),dtype=int)
    for i in range(period-1,len(close)):
        if i==period-1:direction[i]=1;continue
        if not (upper[i]<upper[i-1] or close[i-1]>upper[i-1]):upper[i]=upper[i-1]
        if not (lower[i]>lower[i-1] or close[i-1]<lower[i-1]):lower[i]=lower[i-1]
        direction[i]=(-1 if close[i]<lower[i] else 1) if direction[i-1]==1 else (1 if close[i]>upper[i] else -1)
    return direction


def signals(a,family,variant):
    _,o,h,l,c=a.T;direction=np.zeros(len(c),dtype=int)
    if family=='macd_rsi':
        m=ema(c,10)-ema(c,15);s=ema(m,5);r=rsi(c,10);up=cross(m,s);down=cross(s,m);ru=cross(r,np.full(len(r),50.));rd=cross(np.full(len(r),50.),r)
        if variant=='strict':buy=up&ru;sell=down&rd
        else:
            recent=lambda x:pd.Series(x).rolling(3,min_periods=1).max().to_numpy().astype(bool)
            buy=recent(up)&recent(ru)&(up|ru)&(m>s)&(r>50);sell=recent(down)&recent(rd)&(down|rd)&(m<s)&(r<50)
    elif family=='ma_macd_rsi':
        mode,slow=variant.split('_');fast=int(mode[3:]);slow=int(slow)
        ma=lambda n:pd.Series(c).rolling(n).mean().to_numpy() if mode.startswith('sma') else ema(c,n)
        f=ma(fast);s=ma(slow);m=ema(c,10)-ema(c,20);sig=ema(m,9);r=rsi(c,14)
        buy=cross(f,s)&(m>sig)&(r>50)&(r<80);sell=cross(s,f)&(m<sig)&(r<50)&(r>20)
    else:
        period,mult=map(int,variant.split('_'));trend=supertrend(h,l,c,period,mult);dots=sar(h,l,c)
        buy=(trend==1)&(np.r_[0,trend[:-1]]==-1)&(dots<c);sell=(trend==-1)&(np.r_[0,trend[:-1]]==1)&(dots>c)
    direction[buy]=1;direction[sell]=-1;direction[:300]=0
    return direction


def replay(parts,configs,periods):
    results={name:{config_id(c):[] for c in configs} for name in periods}
    for asset,base in parts:
        if len(base)<305:continue
        for tf in sorted({c['tf'] for c in configs}):
            bars=aggregate(base,tf)
            if len(bars)<301:continue
            for family,variant in sorted({(c['family'],c['variant']) for c in configs if c['tf']==tf}):
                direction=signals(bars,family,variant);indexes=np.flatnonzero(direction)
                for conf in (c for c in configs if c['tf']==tf and c['family']==family and c['variant']==variant):
                    cid=config_id(conf)
                    for period,(start,end) in periods.items():
                        for latency in (0,5):
                            available=-1
                            for i in indexes:
                                decision=int(bars[i,0]+tf*1000);entry=decision+latency*1000;settle=entry+conf['expiry']*1000
                                if decision<start or settle>=end or entry<available:continue
                                ei=(entry-int(base[0,0]))//5000;si=(settle-int(base[0,0]))//5000
                                if ei<=0 or si>=len(base) or ei<0:continue
                                if int(base[ei,0])!=entry or int(base[si,0])!=settle:raise ValueError('Settlement alignment failure')
                                move=(base[si,1]-base[ei,1])*direction[i];outcome=1 if move>0 else -1 if move<0 else 0
                                previous=np.sign(base[ei-1,4]-base[ei-1,1]);actual=np.sign(base[si,1]-base[ei,1])
                                results[period][cid].append({'asset':asset,'decision':decision,'entry':entry,'settle':settle,'direction':int(direction[i]),'outcome':outcome,'latency':latency,
                                  'call':int(actual),'put':int(-actual),'previous':int(actual*previous)})
                                available=settle
    return results


def wilson(w,n):
    if not n:return 0.
    z=1.96;p=w/n
    return (p+z*z/(2*n)-z*math.sqrt(p*(1-p)/n+z*z/(4*n*n)))/(1+z*z/n)


def summarize(rows,latency=0):
    rows=[r for r in rows if r['latency']==latency];w=sum(r['outcome']==1 for r in rows);loss=sum(r['outcome']==-1 for r in rows);ties=len(rows)-w-loss;n=w+loss
    daily=defaultdict(float);assets=defaultdict(lambda:[0,0,0])
    for r in rows:
        ret=.8 if r['outcome']==1 else -1 if r['outcome']==-1 else 0
        daily[iso(r['entry'])[:10]]+=ret;assets[r['asset']][0]+=r['outcome']==1;assets[r['asset']][1]+=r['outcome']==-1;assets[r['asset']][2]+=r['outcome']==0
    values=np.array(list(daily.values()));bootstrap=None
    if len(values)>=3:
        rng=np.random.default_rng(55);means=rng.choice(values,(5000,len(values)),replace=True).mean(axis=1);bootstrap=float(np.quantile(means,.025))
    baselines={k:{'wins':sum(r[k]==1 for r in rows),'losses':sum(r[k]==-1 for r in rows),'net80':sum(.8 if r[k]==1 else -1 if r[k]==-1 else 0 for r in rows)} for k in ('call','put','previous')}
    return {'trades':len(rows),'wins':w,'losses':loss,'ties':ties,'win_rate':w/n if n else None,'wilson_lower95':wilson(w,n),'p_greater_breakeven80':float(binomtest(w,n,1/1.8,alternative='greater').pvalue) if n else 1.,
      'net_units':{str(p):p*w-loss for p in (.7,.8,.9,.92)},'break_even_payout':loss/w if w else None,'utc_days':len(daily),'daily_net80':dict(daily),'day_bootstrap_lower95_mean_net80':bootstrap,
      'assets':{a:{'wins':v[0],'losses':v[1],'ties':v[2],'net80':.8*v[0]-v[1]} for a,v in assets.items()},'benchmarks':baselines}


def qualifies(r,trials=144,days=3):
    return (r['wins']+r['losses']>=200 and r['utc_days']>=days and r['wilson_lower95']>1/1.8 and r['p_greater_breakeven80']<.05/trials
     and (r['day_bootstrap_lower95_mean_net80'] or -1)>0 and sum(a['net80']>0 for a in r['assets'].values())>=2)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--po',type=Path,required=True);parser.add_argument('--october',type=Path,required=True);parser.add_argument('--november',type=Path,required=True);parser.add_argument('--out',type=Path,default=ROOT/'research/video_strategies_v1/results');args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    plan_path=ROOT/'research/video_strategies_v1/plan.json';plan=json.loads(plan_path.read_text())
    configs=[{'family':f,'variant':v,'tf':tf,'expiry':e} for f,vs in VARIANTS.items() for v in vs for tf in plan['sensitivity']['timeframes_seconds'] for e in plan['sensitivity']['expiries_seconds']]
    if len(configs)!=144:raise ValueError('Unexpected trial count')
    po,po_meta=load_po(args.po);october,oct_meta=load_proxy(args.october)
    phases={'po_development':(stamp('2026-09-27'),stamp('2026-10-05 07:23:55')),'po_validation':(stamp('2026-10-05 07:23:55'),stamp('2026-10-05 18:10:50'))}
    results={};print('Replay PO',len(po),'segments',flush=True)
    for phase,rows in replay(po,configs,phases).items():results[phase]={cid:{'base':summarize(trades),'latency5':summarize(trades,5)} for cid,trades in rows.items()}
    print('Replay October proxy',len(october),'segments',flush=True)
    for phase,rows in replay(october,configs,{'proxy_development':(stamp('2026-10-01'),stamp('2026-10-05')),'proxy_validation':(stamp('2026-10-05'),stamp('2026-10-08'))}).items():results[phase]={cid:{'base':summarize(trades),'latency5':summarize(trades,5)} for cid,trades in rows.items()}
    candidates=[c for c in configs if qualifies(results['proxy_validation'][config_id(c)]['base'])]
    candidates.sort(key=lambda c:(-results['proxy_validation'][config_id(c)]['base']['wilson_lower95'],config_id(c)))
    selected=candidates[0] if candidates else None
    primaries=[plan['video'+str(n)]['primary'] for n in (2,3,4)];confirmatory={config_id(c):c for c in primaries}
    if selected:confirmatory[config_id(selected)]=selected
    november,nov_meta=load_proxy(args.november);print('Replay fresh proxy, fixed primaries and selected candidate only',len(confirmatory),flush=True)
    raw=replay(november,list(confirmatory.values()),{'fresh_proxy':(stamp('2026-11-01'),stamp('2026-11-08'))})['fresh_proxy']
    results['fresh_proxy']={cid:{'base':summarize(rows),'latency5':summarize(rows,5),'passes_proxy_gate':qualifies(summarize(rows),trials=4,days=5) and summarize(rows,5)['net_units']['0.8']>0} for cid,rows in raw.items()}
    report={'plan_sha256':hashlib.sha256(plan_path.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'trials':len(configs),'sources':{'pocket_option':po_meta,'october_proxy':oct_meta,'fresh_proxy':nov_meta},'selected':selected,'qualifying_validation_candidates':len(candidates),'primaries':primaries,'results':results,'old_po_final_evaluated':False,'live_approved':False}
    (args.out/'summary.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    rows=[{'config':cid,**row} for cid,trades in raw.items() for row in trades]
    with (args.out/'fresh_proxy_trades.csv').open('w') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else ['config']);writer.writeheader();writer.writerows(rows)
    print('SELECTED',selected,flush=True)
    for cid,result in results['fresh_proxy'].items():print(cid,json.dumps(result['base']), 'PASS',result['passes_proxy_gate'],flush=True)


if __name__=='__main__':main()
