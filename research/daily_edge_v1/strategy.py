"""Eight fixed daily hypotheses. Signals use closed bars, never execution-bar data."""
import numpy as np
import pandas as pd

CANDIDATES=('sma200_trend','ema50_200_cross','donchian55_20','donchian20_10','chandelier22_3atr','monthly10_sma','rsi2_bull_pullback','range_fade')


def seeded(values,n,alpha=None):
    a=np.full(len(values),np.nan)
    if len(values)<n:return a
    value=float(np.mean(values[:n]));a[n-1]=value;k=alpha if alpha is not None else 2/(n+1)
    for i in range(n,len(values)):value+=k*(values[i]-value);a[i]=value
    return a


def indicators(bars):
    f=pd.DataFrame(bars).sort_values('ts').reset_index(drop=True)
    if f.ts.duplicated().any():raise ValueError('Duplicate dates')
    c=f.close.to_numpy();prior=np.r_[c[0],c[:-1]];f['sma200']=f.close.rolling(200).mean();f['ema50']=seeded(c,50);f['ema200']=seeded(c,200);f['mean20']=f.close.rolling(20).mean();f['mean5']=f.close.rolling(5).mean();f['std20']=f.close.rolling(20).std()
    tr=np.maximum.reduce([f.high.to_numpy()-f.low.to_numpy(),abs(f.high.to_numpy()-prior),abs(f.low.to_numpy()-prior)]);f['atr']=seeded(tr,14,1/14)
    up=seeded(np.maximum(c-prior,0),2,.5);down=seeded(np.maximum(prior-c,0),2,.5)
    with np.errstate(divide='ignore',invalid='ignore'):f['rsi2']=np.where(up+down>0,100*up/(up+down),50)
    for n in (10,20,55):f['high'+str(n)]=f.high.shift().rolling(n).max();f['low'+str(n)]=f.low.shift().rolling(n).min()
    f['highest22']=f.close.rolling(22).max();f['lowest22']=f.close.rolling(22).min()
    months=pd.to_datetime(f.ts,unit='ms',utc=True).dt.tz_localize(None).dt.to_period('M');monthly=f.groupby(months).close.last();previous=monthly.shift();ma=monthly.rolling(10).mean().shift();mapping={str(k):(1 if previous[k]>ma[k] else -1 if previous[k]<ma[k] else 0) for k in monthly.index}
    f['month_decision']=months.ne(months.shift());f['monthly_bias']=[mapping[str(k)] for k in months]
    return f


def decision(row,name,kind,side=0,held=0):
    if not np.isfinite(row.atr) or row.atr<=0 or not np.isfinite(row.sma200):return 0,False
    long=row.close>row.sma200;short=kind=='forex' and row.close<row.sma200
    desired=0;exit=False
    if name=='sma200_trend':desired=1 if long else -1 if short else 0;exit=bool(side and desired!=side)
    elif name=='ema50_200_cross':
        desired=1 if long and row.ema50>row.ema200 else -1 if short and row.ema50<row.ema200 else 0;exit=bool(side and desired!=side)
    elif name in ('donchian55_20','donchian20_10','chandelier22_3atr'):
        n=55 if name=='donchian55_20' else 20;out=20 if n==55 else 10
        desired=1 if long and row.close>row['high'+str(n)] else -1 if short and row.close<row['low'+str(n)] else 0
        exit=bool(side==1 and (row.close<row['low'+str(out)] or not long) or side==-1 and (row.close>row['high'+str(out)] or not short))
    elif name=='monthly10_sma':
        if row.month_decision:
            desired=1 if row.monthly_bias==1 else -1 if kind=='forex' and row.monthly_bias==-1 else 0;exit=bool(side and desired!=side)
    elif name=='rsi2_bull_pullback':
        desired=1 if long and row.rsi2<10 else -1 if short and row.rsi2>90 else 0
        exit=bool(side==1 and row.close>row.mean5 or side==-1 and row.close<row.mean5 or held>=5)
    elif name=='range_fade':
        z=(row.close-row.mean20)/max(1e-12,row.std20)
        quiet=abs(row.ema50-row.ema200)<row.atr
        desired=1 if quiet and z<-2 and row.rsi2<10 else -1 if kind=='forex' and quiet and z>2 and row.rsi2>90 else 0
        exit=bool(side==1 and row.close>row.mean20 or side==-1 and row.close<row.mean20 or held>=10)
    else:raise ValueError('Unknown candidate')
    return desired,exit
