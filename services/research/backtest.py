"""KAOS research-only 5-second OHLC replay. No order placement or arbitrary code execution."""
import math
from collections import defaultdict

def ema(a,n):
    out=[]; v=None; k=2/(n+1)
    for x in a:
        v=x if v is None else v+k*(x-v);out.append(v)
    return out

def rsi(a,n=11):
    out=[None]*len(a)
    if len(a)<=n:return out
    gains=[max(a[i]-a[i-1],0) for i in range(1,len(a))]
    losses=[max(a[i-1]-a[i],0) for i in range(1,len(a))]
    g=sum(gains[:n])/n;l=sum(losses[:n])/n
    for i in range(n,len(a)):
        if i>n:g=(g*(n-1)+gains[i-1])/n;l=(l*(n-1)+losses[i-1])/n
        out[i]=100*g/(g+l) if g+l else 50
    return out

def signal_series(b,rule,params):
    c=[x['close'] for x in b]
    if rule=='macd_rsi':
        f=ema(c,int(params.get('fast',10)));s=ema(c,int(params.get('slow',19)))
        m=[x-y for x,y in zip(f,s)]; sig=ema(m,int(params.get('signal',7)))
        h=[x-y for x,y in zip(m,sig)];r=rsi(c,int(params.get('rsi',11)))
        return [1 if i>0 and h[i-1]<=0<h[i] and r[i] is not None and r[i]>50 else -1 if i>0 and h[i-1]>=0>h[i] and r[i] is not None and r[i]<50 else 0 for i in range(len(b))]
    if rule=='kaos_sweep_reclaim':
        # Independent price-action experiment: closed-candle liquidity sweep + reclaim.
        # Prior extremes exclude the signal candle; no future bars or repainting.
        lookback=int(params.get('lookback',12))
        min_wick=float(params.get('min_wick_ratio',0.45))
        min_close=float(params.get('close_position',0.60))
        cooldown=int(params.get('cooldown_bars',3))
        if not (5<=lookback<=100 and 0<=min_wick<=1 and .5<=min_close<=1 and 0<=cooldown<=100):
            raise ValueError('Invalid sweep/reclaim parameters: lookback 5-100, min_wick_ratio 0-1, close_position 0.5-1, cooldown_bars 0-100')
        out=[0]*len(b);last=-100000
        for i in range(lookback,len(b)):
            if i-last<=cooldown:continue
            bar=b[i];lo=min(x['low'] for x in b[i-lookback:i]);hi=max(x['high'] for x in b[i-lookback:i])
            span=bar['high']-bar['low']
            if span<=0:continue
            body_low=min(bar['open'],bar['close']);body_high=max(bar['open'],bar['close'])
            lower=(body_low-bar['low'])/span;upper=(bar['high']-body_high)/span
            close_loc=(bar['close']-bar['low'])/span
            # Strict prior-level sweep and close back inside, with rejection wick.
            if bar['low']<lo and bar['close']>lo and lower>=min_wick and close_loc>=min_close:
                out[i]=1;last=i
            elif bar['high']>hi and bar['close']<hi and upper>=min_wick and close_loc<=1-min_close:
                out[i]=-1;last=i
        return out
    if rule=='streak':
        n=int(params.get('streak',2));out=[]
        for i in range(len(b)):
            w=b[max(0,i-n+1):i+1]
            out.append(1 if len(w)==n and all(x['close']>x['open'] for x in w) else -1 if len(w)==n and all(x['close']<x['open'] for x in w) else 0)
        return out
    raise ValueError('Supported strategies: macd_rsi, streak, kaos_sweep_reclaim. Arbitrary Pine/JS is not executed.')

def backtest(req):
    raw=req.get('candles');rule=req.get('strategy','macd_rsi');params=req.get('params') or {}
    if not isinstance(raw,list) or len(raw)<50 or len(raw)>250000:raise ValueError('Provide 50–250,000 five-second candles')
    if rule not in ('macd_rsi','streak','candidate7b_spec_reconstruction','kaos_sweep_reclaim'):raise ValueError('Unsupported strategy.')
    tfs=[5,15,30,60] if req.get('test_all') else [int(req.get('timeframe',5))]
    exps=[5,10,15,30,60] if req.get('test_all') else [int(req.get('expiry',15))]
    if any(x not in (5,15,30,60) for x in tfs) or any(x not in (5,10,15,30,60) for x in exps):raise ValueError('Invalid timeframe or expiry')
    normalized=[]
    for x in raw:
        try:
            ts=int(float(x.get('ts',x.get('timestamp'))));ts=ts*1000 if ts<100000000000 else ts
            o,h,l,c=[float(x[k]) for k in ('open','high','low','close')]
        except (KeyError,TypeError,ValueError):raise ValueError('Each candle requires ts, open, high, low, close')
        if not all(math.isfinite(v) for v in (o,h,l,c)) or l>min(o,c) or h<max(o,c):raise ValueError('Invalid candle OHLC')
        normalized.append({'ts':ts,'open':o,'high':h,'low':l,'close':c})
    normalized.sort(key=lambda x:x['ts']); unique={x['ts']:x for x in normalized};raw=list(unique.values())
    # Split gaps before indicators, and do not settle across gaps.
    segments=[];part=[]
    for x in raw:
        if part and x['ts']-part[-1]['ts']!=5000:segments.append(part);part=[]
        part.append(x)
    if part:segments.append(part)
    if rule=='candidate7b_spec_reconstruction':
        from candidate7b_replay import replay
        return replay(segments)
    summaries=[];trades=[]
    for tf in tfs:
      for expiry in exps:
        outcomes=defaultdict(int);exposure=0
        for seg in segments:
            if len(seg)<max(60,tf//5*35):continue
            # Group by absolute aligned bar start, reject partial timeframe bars.
            groups=defaultdict(list)
            for x in seg:groups[x['ts']//(tf*1000)].append(x)
            bars=[]
            for g,items in sorted(groups.items()):
                if len(items)!=tf//5 or items[0]['ts']!=g*tf*1000:continue
                bars.append({'ts':items[0]['ts'],'open':items[0]['open'],'high':max(v['high'] for v in items),'low':min(v['low'] for v in items),'close':items[-1]['close']})
            if len(bars)<35:continue
            by_ts={x['ts']:x for x in seg};sigs=signal_series(bars,rule,params);busy=-1
            exposure+=len(seg)*5/3600
            for i in range(30,len(bars)):
                side=sigs[i]
                if not side:continue
                entry_ts=bars[i]['ts']+tf*1000;exit_ts=entry_ts+expiry*1000
                if entry_ts<busy or entry_ts not in by_ts or exit_ts not in by_ts:continue
                entry=by_ts[entry_ts]['open'];settle=by_ts[exit_ts]['open']
                result='T' if entry==settle else 'W' if (settle-entry)*side>0 else 'L'
                outcomes[result]+=1;busy=exit_ts
                if len(trades)<20000:trades.append({'tf':tf,'expiry':expiry,'ts':entry_ts,'direction':'BUY' if side==1 else 'SELL','entry':entry,'settlement':settle,'result':result})
        w,l,t=(outcomes[k] for k in ('W','L','T'));count=w+l+t
        summaries.append({'tf':tf,'expiry':expiry,'trades':count,'wins':w,'losses':l,'ties':t,'win_rate':round(100*w/(w+l),2) if w+l else None,'market_hours':round(exposure,3),'trades_per_market_hour':round(count/exposure,2) if exposure else 0,'passes_targets':bool(w+l and w/(w+l)>=.60 and count/exposure>=12) if exposure else False})
    return {'mode':'offline-research-only','strategy':rule,'summary':summaries,'trades':trades,'trades_truncated':len(trades)>=20000,'warning':'Next-candle open settlement proxy; broker fills unverified. One asset per request; test-all rates are market-hours, not portfolio wall-clock throughput.'}
