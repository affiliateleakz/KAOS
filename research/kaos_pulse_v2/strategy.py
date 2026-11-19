"""KAOS PULSE v2: causal research signals and paper-only quote intents."""
import math
import numpy as np
import pandas as pd


def wilder(values,n):
    a=np.asarray(values,dtype=float);out=np.full(len(a),np.nan)
    if len(a)<n:return out
    out[n-1]=np.mean(a[:n])
    for i in range(n,len(a)):out[i]=(out[i-1]*(n-1)+a[i])/n
    return out


def indicators(bars):
    f=pd.DataFrame(bars).copy();c=f.close.to_numpy();previous=np.r_[c[0],c[:-1]]
    for n in [20,50,200]:f['ema'+str(n)]=f.close.ewm(span=n,adjust=False).mean()
    tr=np.maximum.reduce([f.high.to_numpy()-f.low.to_numpy(),abs(f.high.to_numpy()-previous),abs(f.low.to_numpy()-previous)]);f['atr']=wilder(tr,14)
    change=np.diff(c);up=np.r_[np.nan,wilder(np.maximum(change,0),14)];down=np.r_[np.nan,wilder(np.maximum(-change,0),14)];den=up+down
    f['rsi']=np.divide(100*up,den,out=np.full(len(c),50.),where=den>0);f.loc[~np.isfinite(den),'rsi']=np.nan
    mid=f.close.rolling(20).mean();sd=f.close.rolling(20).std(ddof=0);f['bb_low']=mid-2*sd;f['bb_high']=mid+2*sd
    net=(f.close-f.close.shift(20)).abs();path=f.close.diff().abs().rolling(20).sum();f['er']=(net/path.replace(0,np.nan)).fillna(0).clip(0,1)
    f['z']=(f.close-f.ema20)/f.atr.replace(0,np.nan);f['z_slow']=(f.close-f.ema50)/f.atr.replace(0,np.nan)
    return f


def signals(f,trend_guard=False,shorts=False):
    prev=f.shift(1);ready=(np.arange(len(f))>=(249 if trend_guard else 59))&(f.atr>0)&np.isfinite(f.rsi)
    long_stretch=(prev.er<=.28)&(prev.z<=-1)&(prev.rsi<=42)&(prev.close<prev.bb_low)&(prev.z_slow>-2)
    call=long_stretch&(f.er<=.28)&(f.close>=f.bb_low)&(f.close>f.open)&(f.rsi>prev.rsi)
    short_stretch=(prev.er<=.28)&(prev.z>=1)&(prev.rsi>=58)&(prev.close>prev.bb_high)&(prev.z_slow<2)
    put=short_stretch&(f.er<=.28)&(f.close<=f.bb_high)&(f.close<f.open)&(f.rsi<prev.rsi)
    if trend_guard:call&=(f.close>f.ema200)&(f.ema50>f.ema200);put&=(f.close<f.ema200)&(f.ema50<f.ema200)
    return np.where(call&ready,1,np.where(put&ready&shorts,-1,0))


def cost_budget(atr,entry,target_atr,fee_bps,slip_bps):
    if any(not math.isfinite(float(x)) for x in [atr,entry,target_atr,fee_bps,slip_bps]) or min(atr,entry,target_atr)<=0 or min(fee_bps,slip_bps)<0:return False
    return target_atr*atr/entry>=5*2*(fee_bps+slip_bps)/10000


def risk_quantity(equity,entry,stop,risk_fraction=.005,max_notional_fraction=1.,lot_step=.00000001,min_lot=0.,fee_bps=10.,slip_bps=2.):
    values=[equity,entry,stop,risk_fraction,max_notional_fraction,lot_step,min_lot,fee_bps,slip_bps]
    if not all(math.isfinite(float(v)) for v in values) or min(equity,entry,stop,lot_step)<=0 or not 0<risk_fraction<=.01 or not 0<max_notional_fraction<=1 or min(min_lot,fee_bps,slip_bps)<0 or max(fee_bps,slip_bps)>100 or stop>=entry:raise ValueError('Invalid conservative long risk inputs')
    paid=entry*(1+slip_bps/10000);stop_fill=stop*(1-slip_bps/10000);risk=paid-stop_fill+fee_bps/10000*(paid+stop_fill)
    quantity=min(equity*risk_fraction/risk,equity*max_notional_fraction/(paid*(1+fee_bps/10000)))
    quantity=math.floor(quantity/lot_step)*lot_step
    return 0. if quantity<min_lot else quantity


def paper_intent(symbol,bars,tf_seconds,now_ms,quote,trend_guard=True,target_atr=3,fee_bps=10.,slip_bps=2.):
    result={'name':'KAOS PULSE v2','symbol':symbol,'action':'HOLD','executionEnabled':False,'researchOnly':True,'validatedProfitable':False}
    if symbol not in ['BTCUSDT','ETHUSDT','SOLUSDT','BNBUSDT','XRPUSDT','ADAUSDT']:return {**result,'reason':'unsupported_spot_research_symbol'}
    if tf_seconds not in (3600,14400) or target_atr not in (3,4):raise ValueError('Outside frozen parameter grid')
    if isinstance(now_ms,bool) or not isinstance(now_ms,int) or now_ms<=0:raise ValueError('Integer current timestamp required')
    if not all(isinstance(quote.get(k),(int,float)) and not isinstance(quote[k],bool) and math.isfinite(quote[k]) for k in ['bid','ask','observedAt']):raise ValueError('Finite bid/ask timestamp required')
    if not 0<quote['bid']<=quote['ask'] or not 0<=now_ms-quote['observedAt']<=30000:return {**result,'reason':'stale_or_invalid_quote'}
    a=np.asarray(bars,dtype=float);needed=250 if trend_guard else 60
    if not a.size:return {**result,'reason':'insufficient_history'}
    if a.ndim!=2 or a.shape[1]!=5 or not np.isfinite(a).all():raise ValueError('Finite OHLC rows required')
    if len(a)<needed:return {**result,'reason':'insufficient_history'}
    if np.any(a[:,0]%(tf_seconds*1000)) or np.any(np.diff(a[:,0])!=tf_seconds*1000) or np.any(a[:,1:]<=0) or np.any(a[:,3]>np.minimum(a[:,1],a[:,4])) or np.any(a[:,2]<np.maximum(a[:,1],a[:,4])):raise ValueError('Malformed or discontinuous candles')
    decision=int(a[-1,0])+tf_seconds*1000
    if not 0<=now_ms-decision<=120000:return {**result,'reason':'forming_or_stale_signal'}
    frame=indicators(pd.DataFrame(a,columns=['ts','open','high','low','close']))
    if not signals(frame,trend_guard)[-1]:return {**result,'reason':'no_confirmed_reclaim'}
    atr=float(frame.atr.iloc[-1]);entry=float(quote['ask'])
    if not cost_budget(atr,entry,target_atr,fee_bps,slip_bps) or entry-2*atr<=0:return {**result,'reason':'cost_or_stop_filter'}
    return {**result,'action':'BUY','decision':decision,'entryReference':entry,'estimatedEntryFill':entry*(1+slip_bps/10000),'stop':entry-2*atr,'target':entry+target_atr*atr,'maxHoldRequestedBars':24,'feeBpsPerSide':fee_bps,'slippageBpsPerSide':slip_bps}
