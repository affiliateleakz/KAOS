"""Asset-specific calendars, conservative bracket fills and fixed-expiry replay."""
import numpy as np
import pandas as pd
HOUR=3600000


def parts(records,kind):
    rows=sorted(records,key=lambda r:r['ts']);result=[];current=[]
    if len({r['ts'] for r in rows})!=len(rows):raise ValueError('Duplicate quote timestamps')
    for r in rows:
        if current:
            prev=current[-1];gap=r['ts']-prev['end'];bad=False
            if gap<0:raise ValueError('Overlapping source quote intervals')
            if gap>0:
                if kind=='stocks':bad=(r['session_start']==prev['session_start'] or prev['end']!=prev['session_end'])
                elif kind=='forex':bad=not (pd.Timestamp(prev['end'],unit='ms',tz='UTC').weekday()==4 and pd.Timestamp(r['ts'],unit='ms',tz='UTC').weekday() in (6,0) and gap<=80*HOUR)
                else:bad=True
            if bad:result.append(current);current=[]
        current.append(r)
    if current:result.append(current)
    return result


def requested(base,tf,kind):
    if tf==3600:return pd.DataFrame(base)
    groups={}
    for r in base:
        anchor=r['session_start'] if kind=='stocks' else 0
        start=anchor+(r['ts']-anchor)//(tf*1000)*(tf*1000);end=min(start+tf*1000,r['session_end']) if kind=='stocks' else start+tf*1000
        groups.setdefault((start,end),[]).append(r)
    bars=[]
    for (start,end),rows in sorted(groups.items()):
        if [r['ts'] for r in rows]!=list(range(start,end,HOUR)) or rows[-1]['end']!=end:continue
        bars.append({'ts':start,'end':end,'open':rows[0]['open'],'high':max(r['high'] for r in rows),'low':min(r['low'] for r in rows),'close':rows[-1]['close']})
    return pd.DataFrame(bars)


def brackets(asset,base,frame,sig,atr,target,stop_multiple,bounds,kind,budget=None,stress=False,dividends=()):
    a=pd.DataFrame(base);times=a.ts.to_numpy();ends=a.end.to_numpy();op=a.open.to_numpy();hi=a.high.to_numpy();lo=a.low.to_numpy();cl=a.close.to_numpy();rows=[];available=0
    fee_bps=10 if kind=='crypto' else 0;slip_bps=2 if kind=='crypto' else 1;carry_bps=2 if kind=='forex' else 0
    fee=fee_bps*(2 if stress else 1)/10000;slip=slip_bps*(2 if stress else 1)/10000;carry=carry_bps*(2 if stress else 1)/10000
    for i in np.flatnonzero(sig):
        if i+24>=len(frame):continue
        decision=int(frame.end.iloc[i]);deadline=int(frame.end.iloc[i+24]);ei=int(np.searchsorted(times,decision))+(1 if stress else 0);last=int(np.searchsorted(ends,deadline))
        if decision<bounds[0] or deadline>=bounds[1] or ei<available or ei>=len(a) or last>=len(a) or ei>last or ends[last]!=deadline:continue
        side=int(sig[i]);raw=float(op[ei]);vol=float(atr[i]);risk=stop_multiple*vol
        if not np.isfinite(vol) or vol<=0 or raw-max(target,stop_multiple)*vol<=0:continue
        if budget is not None and not budget(vol,raw,target,fee_bps,slip_bps):continue
        stop=raw-side*risk;tp=raw+side*target*vol;exit_price=float(cl[last]);exit_i=last;exit_ts=deadline;reason='time'
        for j in range(ei,last+1):
            if (side>0 and op[j]<=stop) or (side<0 and op[j]>=stop):exit_i=j;exit_price=float(op[j]);reason='stop_gap';break
            if (side>0 and op[j]>=tp) or (side<0 and op[j]<=tp):exit_i=j;exit_price=tp;reason='target';break
            hit_stop=lo[j]<=stop if side>0 else hi[j]>=stop;hit_target=hi[j]>=tp if side>0 else lo[j]<=tp
            if hit_stop:exit_i=j;exit_price=stop;reason='stop';break
            if hit_target:exit_i=j;exit_price=tp;reason='target';break
        if reason!='time':exit_ts=int(ends[exit_i]) # Conservative hour-bucket end for carry, not exact accepted fill.
        paid=raw*(1+side*slip);received=exit_price*(1-side*slip);holding=raw*carry*(exit_ts-times[ei])/86400000
        dividend=sum(d['amount'] for d in dividends if side>0 and times[ei]<d['ts']<=exit_ts)
        net=side*(received-paid)-fee*(abs(paid)+abs(received))-holding+dividend
        rows.append({'asset':asset,'entry':int(times[ei]),'exit':exit_ts,'side':side,'entryPrice':paid,'exitPrice':received,'netR':net/risk,'netBps':net/raw*10000,'grossDividendsPerUnit':dividend,'reason':reason,'executionEnabled':False});available=exit_i+1
    return rows


def binary(asset,a,frame,sig,expiry_bars,bounds,stress=False):
    result=[];available=-1;start=int(a[0,0]);tf=int(frame.end.iloc[0]-frame.ts.iloc[0])
    for i in np.flatnonzero(sig):
        decision=int(frame.end.iloc[i]);entry=decision+(5000 if stress else 0);end=entry+expiry_bars*tf
        if decision<bounds[0] or end>=bounds[1] or entry<available:continue
        ei=(entry-start)//5000;si=(end-start)//5000
        if ei<1 or si>=len(a):continue
        if a[ei,0]!=entry or a[si,0]!=end:raise ValueError('Unobserved binary settlement')
        side=int(sig[i]);price=a[ei,1]*(1+side*.0001) if stress else a[ei,1];outcome=int(np.sign((a[si,1]-price)*side))
        result.append({'asset':asset,'entry':entry,'exit':end,'outcome':outcome,'executionEnabled':False});available=end
    return result
