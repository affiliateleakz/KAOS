"""Causal research signals and conservative offline fills. No order interface."""
import numpy as np
import pandas as pd


def features(bars,warmup=250):
    f=pd.DataFrame(bars,columns=['ts','open','high','low','close'])
    c=f.close;prev=c.shift(1)
    for n in (20,50,200):f['ema'+str(n)]=c.ewm(span=n,adjust=False).mean()
    tr=np.maximum(f.high-f.low,np.maximum((f.high-prev).abs(),(f.low-prev).abs()))
    if len(f):tr.iloc[0]=f.high.iloc[0]-f.low.iloc[0]
    # Explicit Wilder seed, then recursive smoothing.
    atr=np.full(len(f),np.nan)
    if len(f)>=14:
        atr[13]=tr.iloc[:14].mean()
        for i in range(14,len(f)):atr[i]=(atr[i-1]*13+tr.iloc[i])/14
    f['atr']=atr
    f['prior_high']=f.high.rolling(20).max().shift(1);f['prior_low']=f.low.rolling(20).min().shift(1)
    f['mean']=c.rolling(20).mean();f['sd']=c.rolling(20).std(ddof=0)
    f['ready']=(np.arange(len(f))>=warmup-1)&(f.atr>0)
    return f


def spot_signals(f,family):
    trend=(f.ema50>f.ema200)&(f.close>f.ema200)
    if family=='breakout20':s=(f.close>f.prior_high)&(f.close.shift(1)<=f.prior_high.shift(1))
    elif family=='pullback20':s=(f.low.shift(1)<=f.ema20.shift(1))&(f.close.shift(1)<=f.ema20.shift(1))&(f.close>f.ema20)&(f.close>f.open)
    elif family=='trend_cross':s=(f.ema20>f.ema50)&(f.ema20.shift(1)<=f.ema50.shift(1))&(f.close>f.open)
    elif family=='always_long':return f.ready.to_numpy()
    elif family=='trend_long':return (f.ready&(f.close>f.ema200)).to_numpy()
    else:raise ValueError('Unknown spot family')
    return (s&trend&f.ready).to_numpy()


def binary_signals(f,family):
    c=f.close;p=c.shift(1);green=c>f.open;red=c<f.open
    if family=='breakout20':
        call=(c>f.prior_high)&(p<=f.prior_high.shift(1))&(f.ema20>f.ema50)
        put=(c<f.prior_low)&(p>=f.prior_low.shift(1))&(f.ema20<f.ema50)
    elif family=='pullback20':
        call=(f.low.shift(1)<=f.ema20.shift(1))&(p<=f.ema20.shift(1))&(c>f.ema20)&green&(f.ema20>f.ema50)
        put=(f.high.shift(1)>=f.ema20.shift(1))&(p>=f.ema20.shift(1))&(c<f.ema20)&red&(f.ema20<f.ema50)
    elif family=='range_reclaim':
        lower=f['mean']-2*f.sd;upper=f['mean']+2*f.sd;quiet=(f.ema20-f.ema50).abs()<f.atr
        call=(p<lower.shift(1))&(c>=lower)&green&quiet
        put=(p>upper.shift(1))&(c<=upper)&red&quiet
    else:raise ValueError('Unknown binary family')
    return np.where(call&f.ready,1,np.where(put&f.ready,-1,0))


def spot_exit(a,ei,end,stop,target):
    """Inspect observed minute bars, with adverse gap/stop ordering."""
    x=a[ei:end]
    stop_hits=np.flatnonzero(x[:,3]<=stop);target_hits=np.flatnonzero(x[:,2]>=target)
    si=int(stop_hits[0]) if len(stop_hits) else len(x)
    ti=int(target_hits[0]) if len(target_hits) else len(x)
    if si<len(x) and si<=ti:
        ix=ei+si;return ix,float(min(stop,a[ix,1])),'stop'
    if ti<len(x):return ei+ti,float(target),'target'
    return end,float(a[end,1]),'time'


def spot_replay(asset,a,f,signal,tf,rr,bounds,stress=False):
    rows=[];available=0;base_start=int(a[0,0]);delay=60000 if stress else 0
    fee=.002 if stress else .001;slip=.0004 if stress else .0002
    for i in np.flatnonzero(signal):
        decision=int(f.ts.iloc[i])+tf*1000;entry=decision+delay;deadline=entry+12*tf*1000
        if decision<bounds[0] or deadline>=bounds[1]:continue
        ei=(entry-base_start)//60000;end=(deadline-base_start)//60000
        if ei<available or ei<1 or end>=len(a):continue
        if a[ei,0]!=entry or a[end,0]!=deadline:raise ValueError('Unobserved fill')
        raw=float(a[ei,1]);risk=2*float(f.atr.iloc[i])
        if risk<=0 or raw-risk<=0:continue
        xi,price,reason=spot_exit(a,ei,end,raw-risk,raw+rr*risk)
        paid=raw*(1+slip);received=price*(1-slip)
        net=(received-paid-fee*(paid+received))/risk
        rows.append({'asset':asset,'decision':decision,'entry':entry,'exit':int(a[xi,0]),'entry_price':paid,'exit_price':received,'risk_distance':risk,'netR':net,'reason':reason,'executionEnabled':False})
        available=xi+1
    return rows


def binary_replay(asset,a,f,signal,tf,expiry,bounds,stress=False):
    rows=[];available=-1;first=int(a[0,0]);delay=5000 if stress else 0
    for i in np.flatnonzero(signal):
        direction=int(signal[i]);decision=int(f.ts.iloc[i])+tf*1000;entry=decision+delay;end=entry+expiry*1000
        if decision<bounds[0] or end>=bounds[1] or entry<available:continue
        ei=(entry-first)//5000;si=(end-first)//5000
        if ei<1 or si>=len(a):continue
        if a[ei,0]!=entry or a[si,0]!=end:raise ValueError('Unobserved binary settlement')
        price=a[ei,1]*(1+direction*.0001) if stress else a[ei,1]
        outcome=int(np.sign((a[si,1]-price)*direction))
        rows.append({'asset':asset,'decision':decision,'entry':entry,'exit':end,'entry_price':float(price),'settlement':float(a[si,1]),'direction':direction,'outcome':outcome,'executionEnabled':False})
        available=end
    return rows


def paper_signal(bars,family='pullback20',tf=300,rr=1.5,as_of_ms=None,symbol=None):
    """Requested-timeframe, complete candles only. Never places an order."""
    a=np.asarray(bars,dtype=float)
    result={'action':'HOLD','executionEnabled':False,'researchOnly':True,'symbol':symbol}
    if symbol not in ('BTCUSDT','ETHUSDT','SOLUSDT','BNBUSDT','XRPUSDT','ADAUSDT'):return {**result,'reason':'unsupported_market'}
    if family not in ('breakout20','pullback20','trend_cross'):raise ValueError('Outside frozen research families')
    if tf not in (300,900) or rr not in (1.5,2.):raise ValueError('Outside frozen research grid')
    if a.ndim!=2 or a.shape[1]!=5 or len(a)<250:return {**result,'reason':'insufficient_history'}
    if not np.isfinite(a).all() or np.any(a[:,1:]<=0) or np.any(a[:,3]>np.minimum(a[:,1],a[:,4])) or np.any(a[:,2]<np.maximum(a[:,1],a[:,4])):raise ValueError('Invalid OHLC')
    if np.any(np.diff(a[:,0])!=tf*1000) or np.any(a[:,0]%(tf*1000)):raise ValueError('Require continuous aligned candles')
    closed=int(a[-1,0])+tf*1000
    if as_of_ms is None or closed>as_of_ms or as_of_ms-closed>60000:return {**result,'reason':'forming_or_stale_candle'}
    f=features(a)
    if not spot_signals(f,family)[-1]:return {**result,'reason':'no_setup'}
    return {**result,'action':'BUY','decision':closed,'atr':float(f.atr.iloc[-1]),'stopDistance':2*float(f.atr.iloc[-1]),'targetRiskMultiple':rr,'maxHoldSeconds':12*tf,'reason':family,'note':'Research setup only; entry must use a subsequently observed price.'}
