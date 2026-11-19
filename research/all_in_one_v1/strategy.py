"""KAOS All-in-one Strategy: fixed causal trend-pullback rules, research only."""
import math
import numpy as np
import pandas as pd

NAME='KAOS All-in-one Strategy'


def average(values,length,alpha=None):
    output=np.full(len(values),np.nan)
    if len(values)<length:return output
    value=float(np.mean(values[:length]));output[length-1]=value;k=alpha if alpha is not None else 2/(length+1)
    for i in range(length,len(values)):value+=k*(values[i]-value);output[i]=value
    return output


def indicators(bars,kind):
    frame=pd.DataFrame(bars).sort_values('ts').reset_index(drop=True)
    if frame.ts.duplicated().any():raise ValueError('Duplicate hourly timestamps')
    higher=[];groups={};incomplete=0
    for bar in frame.to_dict('records'):
        if kind=='stocks':
            anchor=int(bar['session_start']);bucket=anchor+(int(bar['ts'])-anchor)//14400000*14400000;end=min(bucket+14400000,int(bar['session_end']))
        else:bucket=int(bar['ts'])//14400000*14400000;end=bucket+14400000
        groups.setdefault((bucket,end),[]).append(bar)
    for (bucket,end),rows in sorted(groups.items()):
        if [r['ts'] for r in rows]!=list(range(bucket,end,3600000)) or rows[-1]['end']!=end:incomplete+=1;continue
        higher.append({'end':end,'close':rows[-1]['close']})
    if not higher:raise ValueError('No complete four-hour groups')
    high=pd.DataFrame(higher);a=average(high.close.to_numpy(),50);b=average(high.close.to_numpy(),200)
    high['bias']=np.where((high.close>b)&(a>b),1,np.where((high.close<b)&(a<b),-1,0))
    frame=pd.merge_asof(frame.sort_values('end'),high[['end','bias']].sort_values('end'),on='end',direction='backward')
    frame['bias']=frame.bias.fillna(0).astype(int)
    c=frame.close.to_numpy();frame['ema20']=average(c,20);frame['ema50']=average(c,50)
    previous=np.r_[c[0],c[:-1]];tr=np.maximum.reduce([frame.high.to_numpy()-frame.low.to_numpy(),np.abs(frame.high.to_numpy()-previous),np.abs(frame.low.to_numpy()-previous)])
    frame['atr']=average(tr,14,1/14)
    gap=[]
    for i,row in frame.iterrows():
        if not i:gap.append(False);continue
        prev=frame.iloc[i-1];delta=row.ts-prev.end
        if kind=='stocks':bad=delta>0 and (row.session_start==prev.session_start or prev.end!=prev.session_end)
        elif kind=='crypto':bad=delta>0
        else:bad=0<delta<40*3600000
        gap.append(bool(bad))
    frame['quote_gap']=gap
    return frame,{'complete_four_hour_bars':len(high),'incomplete_four_hour_groups_excluded':incomplete,'hourly_bars':len(frame),'quote_gaps':sum(gap)}


def signals(frame,kind):
    result={};setup=None
    for i,row in frame.iterrows():
        bias=int(row.bias)
        if row.quote_gap or not bias or (kind in ('stocks','crypto') and bias<0) or not all(math.isfinite(v) for v in (row.ema20,row.ema50,row.atr)):
            setup=None;continue
        if setup and (setup['side']!=bias or setup['age']>=6):setup=None
        zone_low=min(row.ema20,row.ema50);zone_high=max(row.ema20,row.ema50)
        if setup is None and row.low<=zone_high and row.high>=zone_low:setup={'side':bias,'low':row.low,'high':row.high,'age':0}
        if setup is None:continue
        setup['low']=min(setup['low'],row.low);setup['high']=max(setup['high'],row.high)
        prev=frame.iloc[i-1] if i else row
        confirmed=(bias==1 and row.close>row.open and row.close>prev.high and row.close>row.ema20) or (bias==-1 and row.close<row.open and row.close<prev.low and row.close<row.ema20)
        if confirmed:
            stop=setup['low']-.25*row.atr if bias==1 else setup['high']+.25*row.atr
            result[i]={'side':bias,'stop':float(stop),'atr':float(row.atr),'signal_close':float(row.close),'signal_ts':int(row.end),'setup_bars':setup['age']+1};setup=None
        else:setup['age']+=1
    return result
