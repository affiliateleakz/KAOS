"""KAOS Strategy SR1.1: faithful port of the extension's closed-candle S/R baseline.

Four setup families: trend-aligned support/resistance rejection, failed-break reclaim,
breakout retest, and 15-second pullback continuation. This is not a trained AI.
"""
import math
CFG={'name':'KAOS_STRATEGY','version':'SR1.1','srLookback':20,'expiries':[15,20,25]}


def aggregate(rows,seconds):
    output=[];bar=None;period=seconds*1000
    for row in rows:
        ts=row['ts'];end=row.get('closeTs',ts+5000)
        if not end>ts:continue
        bucket=ts//period*period
        if bar is None or bar['ts']!=bucket:
            if bar:output.append(bar)
            bar={'ts':bucket,'open':row['open'],'high':row['high'],'low':row['low'],'close':row['close'],'closeTs':end}
        else:
            bar.update(high=max(bar['high'],row['high']),low=min(bar['low'],row['low']),close=row['close'],closeTs=max(bar['closeTs'],end))
    if bar:output.append(bar)
    return [row for row in output if row['closeTs']>=row['ts']+period-1]


def ema(values,n):
    if len(values)<n:return float('nan')
    value=sum(values[:n])/n;k=2/(n+1)
    for price in values[n:]:value+=k*(price-value)
    return value


def atr(rows,n):
    if len(rows)<n+1:return float('nan')
    return sum(max(rows[i]['high']-rows[i]['low'],abs(rows[i]['high']-rows[i-1]['close']),abs(rows[i]['low']-rows[i-1]['close'])) for i in range(len(rows)-n,len(rows)))/n


def evaluate(rows):
    normalized=[]
    for row in rows:
        item={k:float(row[k]) for k in ('open','high','low','close')};item.update(ts=int(row['ts']),closeTs=int(row.get('closeTs',int(row['ts'])+5000)))
        if not all(math.isfinite(v) for v in item.values()):return None
        normalized.append(item)
    q5,q15,q30,q60=[aggregate(normalized,sec) for sec in (5,15,30,60)]
    if len(q5)<60 or len(q30)<25 or len(q60)<24:return None
    c,p,p2=q5[-1],q5[-2],q5[-3];a30=atr(q30,14)
    if not math.isfinite(a30) or a30<=0:return None
    history=q30[-21:-1]
    support=min(r['low'] for r in history);resistance=max(r['high'] for r in history)
    e9=ema([r['close'] for r in q60],9);e21=ema([r['close'] for r in q60],21)
    bull_context=e9>e21 and q60[-1]['close']>q60[-3]['close'];bear_context=e9<e21 and q60[-1]['close']<q60[-3]['close']
    bull=c['close']>c['open'];bear=c['close']<c['open'];span=max(1e-12,c['high']-c['low']);body=abs(c['close']-c['open'])/span
    lower=(min(c['open'],c['close'])-c['low'])/span;upper=(c['high']-max(c['open'],c['close']))/span
    def pack(engine,direction,expiry,reason):
        return {'engine':engine,'direction':direction,'dir':direction,'expiration':str(expiry)+'s','expiry':expiry,'confidence':None,'strategyVersion':CFG['version'],'reason':reason,'support':support,'resistance':resistance}
    if bull_context and bull and body>=.30 and lower>=.28 and abs(c['low']-support)<=.28*a30 and c['close']>support+.10*a30:return pack('SR_REJECTION','BUY',20,'Support rejection confirmed in 60s uptrend')
    if bear_context and bear and body>=.30 and upper>=.28 and abs(c['high']-resistance)<=.28*a30 and c['close']<resistance-.10*a30:return pack('SR_REJECTION','SELL',20,'Resistance rejection confirmed in 60s downtrend')
    if bull_context and p['low']<support-.12*a30 and p['close']>=support and bull and c['close']>p['high']:return pack('FAILED_BREAK_RECLAIM','BUY',20,'Support sweep and reclaim confirmed')
    if bear_context and p['high']>resistance+.12*a30 and p['close']<=resistance and bear and c['close']<p['low']:return pack('FAILED_BREAK_RECLAIM','SELL',20,'Resistance sweep and reclaim confirmed')
    if bull_context and p2['close']>resistance+.12*a30 and p['low']<=resistance+.28*a30 and p['close']>=resistance and bull and c['close']>p['high']:return pack('BREAKOUT_RETEST','BUY',25,'Breakout and retest confirmed')
    if bear_context and p2['close']<support-.12*a30 and p['high']>=support-.28*a30 and p['close']<=support and bear and c['close']<p['low']:return pack('BREAKOUT_RETEST','SELL',25,'Breakdown and retest confirmed')
    a,b=q15[-1],q15[-2];prior=ema([r['close'] for r in q15[:-1]],9)
    if bull_context and bull and b['close']<b['open'] and a['close']>a['open'] and a['close']>b['high'] and b['low']<=prior and c['close']>b['high']:return pack('TREND_PULLBACK','BUY',15,'15s bullish pullback continuation confirmed')
    if bear_context and bear and b['close']>b['open'] and a['close']<a['open'] and a['close']<b['low'] and b['high']>=prior and c['close']<b['low']:return pack('TREND_PULLBACK','SELL',15,'15s bearish pullback continuation confirmed')
    return None
