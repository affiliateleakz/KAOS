"""Historical Candidate 7B specification reconstruction; NOT verified original B32 source parity.
Closed 5s candles, no lookahead; separate sleeves with their native expiries.
"""
from collections import defaultdict

def ema(values, n):
    out=[];v=None;k=2/(n+1)
    for x in values:
        v=x if v is None else v+k*(x-v);out.append(v)
    return out

def atr(bars,n=14):
    out=[None]*len(bars);v=None
    for i,b in enumerate(bars):
        if i==0:continue
        p=bars[i-1]['close'];tr=max(b['high']-b['low'],abs(b['high']-p),abs(b['low']-p))
        v=tr if v is None else (v*(n-1)+tr)/n
        if i>=n:out[i]=v
    return out

def bars_at(seg,tf):
    step=tf//5;res=[]
    for j in range(0,len(seg)-step+1):
        sub=seg[j:j+step]
        if sub[0]['ts']%(tf*1000)!=0 or sub[-1]['ts']-sub[0]['ts']!=(step-1)*5000:continue
        res.append({'ts':sub[0]['ts'],'end':sub[-1]['ts']+5000,'open':sub[0]['open'],'high':max(x['high'] for x in sub),'low':min(x['low'] for x in sub),'close':sub[-1]['close']})
    return res

def replay(segments):
    totals=defaultdict(lambda:defaultdict(int));trades=[];hours=0
    for seg in segments:
        if len(seg)<160:continue
        b5=bars_at(seg,5);b15=bars_at(seg,15);b30=bars_at(seg,30)
        if len(b30)<20:continue
        hours+=len(seg)*5/3600
        e9=ema([b['close'] for b in b5],9);e21=ema([b['close'] for b in b5],21);a5=atr(b5)
        a15=atr(b15);a30=atr(b30)
        by5={b['end']:i for i,b in enumerate(b5)};by15={b['end']:i for i,b in enumerate(b15)};by30={b['end']:i for i,b in enumerate(b30)}
        raw={b['ts']:b for b in seg};pending=[];seen=set();busy=-1
        # Build setups only at the close of their respective bars.
        for i in range(35,len(b5)-13):
            b=b5[i];now=b['end'];v=a5[i]
            if not v or v<=0:continue
            prev=b5[i-1];side=1 if e9[i]>e21[i] else -1 if e9[i]<e21[i] else 0
            spread=abs(e9[i]-e21[i])/v
            mom=(b['close']-b5[i-3]['close'])/v
            oldmom=(prev['close']-b5[i-4]['close'])/v
            body=abs(b['close']-b['open'])/max(1e-12,b['high']-b['low'])
            if side and spread>=.70 and body>=.50 and abs(b['close']-e9[i])<=1.10*v:
                pullback=(prev['close']<prev['open']) if side==1 else (prev['close']>prev['open'])
                resume=(b['close']>b['open']) if side==1 else (b['close']<b['open'])
                if pullback and resume and mom*side>max(0,oldmom*side):pending.append((now,'RUNNER',side,15))
            # 15s breakout confirmed on a subsequent 15s bar retesting a 6-bar level.
            if now in by15:
                j=by15[now]
                if j>=22 and a15[j-2] and a15[j-2]>0:
                    level_high=max(x['high'] for x in b15[j-8:j-2]);level_low=min(x['low'] for x in b15[j-8:j-2]);av=a15[j-2]
                    pre=b15[j-8:j-2];tight=(max(x['high'] for x in pre)-min(x['low'] for x in pre))<=.75*av
                    br=b15[j-1];rt=b15[j]
                    brbody=abs(br['close']-br['open'])/max(1e-12,br['high']-br['low'])
                    if tight and brbody>=.50:
                        if br['close']>=level_high+.10*av and rt['low']<=level_high+.12*av and rt['close']>level_high:pending.append((now,'BREAKOUT',1,30))
                        if br['close']<=level_low-.10*av and rt['high']>=level_low-.12*av and rt['close']<level_low:pending.append((now,'BREAKOUT',-1,30))
            # 30s resistance rejection: armed, then three completed 5s confirmations.
            if now in by30:
                j=by30[now]
                if j>=18 and a30[j] and a30[j]>0:
                    rej=b30[j];res=max(x['high'] for x in b30[j-8:j]);rg=max(1e-12,rej['high']-rej['low'])
                    upper=(rej['high']-max(rej['open'],rej['close']))/rg
                    body30=abs(rej['close']-rej['open'])/rg
                    if rej['high']>res and rej['close']<res and rej['close']<rej['open'] and upper>=.35 and body30>=.15:
                        # Signal only after 3 subsequent 5s candles, never on rejection itself.
                        confirm_ts=now+15000
                        if confirm_ts in by5:
                            k=by5[confirm_ts]
                            damage=any(b5[q]['close']<=rej['low']-.08*v for q in range(i+1,k+1))
                            if damage and b5[k]['close']<rej['low'] and e9[k]<e21[k] and b5[k]['close']<b5[k-3]['close']:
                                pending.append((confirm_ts,'REVERSAL',-1,30))
        pending.sort(key=lambda x:(x[0],{'REVERSAL':0,'BREAKOUT':1,'RUNNER':2}[x[1]]))
        grouped=defaultdict(list)
        for p in pending:grouped[p[0]].append(p)
        for ts,choices in sorted(grouped.items()):
            if ts<busy or ts not in raw:continue
            if len({x[2] for x in choices})>1:continue
            _,engine,side,expiry=choices[0];exit_ts=ts+expiry*1000
            if exit_ts not in raw:continue
            entry=raw[ts]['open'];settle=raw[exit_ts]['open'];result='T' if entry==settle else 'W' if (settle-entry)*side>0 else 'L'
            totals[engine][result]+=1;totals['COMBINED'][result]+=1;busy=exit_ts
            if len(trades)<20000:trades.append({'tf':'native','expiry':expiry,'ts':ts,'engine':engine,'direction':'BUY' if side>0 else 'SELL','entry':entry,'settlement':settle,'result':result})
    summary=[]
    for engine in ('REVERSAL','RUNNER','BREAKOUT','COMBINED'):
        o=totals[engine];w=o['W'];l=o['L'];t=o['T'];count=w+l+t;rate=100*w/(w+l) if w+l else None;freq=count/hours if hours else 0
        summary.append({'engine':engine,'tf':'mixed','expiry':'native','trades':count,'wins':w,'losses':l,'ties':t,'win_rate':round(rate,2) if rate is not None else None,'market_hours':round(hours,3),'trades_per_market_hour':round(freq,2),'passes_targets':bool(rate is not None and rate>=60 and freq>=12)})
    return {'mode':'offline-research-only','strategy':'candidate7b_spec_reconstruction','summary':summary,'trades':trades,'trades_truncated':len(trades)>=20000,'warning':'SPEC RECONSTRUCTION, NOT ORIGINAL CANDIDATE 7B SOURCE PARITY. ZigZag 5/3/1 regime and efficient-bull-run veto are not implemented; results must not be represented as original 7B. Native expiries: reversal 30s, runner 15s, breakout 30s. Entry/settlement are next 5s candle open proxies.'}
