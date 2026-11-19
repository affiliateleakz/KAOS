"""Reproduce original Pine-pack rule research. No TradingView/Pine runtime claims."""
import argparse,csv,hashlib,json,math
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
RULES={'trend':(2.,3.),'reclaim':(1.5,2.),'breakout':(2.,4.)}


def rma(series,n):
    values=series.to_numpy(dtype=float);out=np.full(len(values),np.nan);seed=[];last=None
    for i,value in enumerate(values):
        if not math.isfinite(value):continue
        if last is None:
            seed.append(value)
            if len(seed)==n:last=sum(seed)/n;out[i]=last
        else:last=(last*(n-1)+value)/n;out[i]=last
    return pd.Series(out,index=series.index)


def indicators(frame):
    f=frame.copy();c=f.close
    f['fast']=c.ewm(span=20,adjust=False).mean();f['slow']=c.ewm(span=50,adjust=False).mean();f['regime']=c.ewm(span=200,adjust=False).mean()
    tr=pd.concat([f.high-f.low,(f.high-c.shift()).abs(),(f.low-c.shift()).abs()],axis=1).max(axis=1)
    f['atr']=rma(tr,14);diff=c.diff();up=rma(diff.clip(lower=0),14);down=rma((-diff).clip(lower=0),14)
    f['rsi']=100-100/(1+up/down);f.loc[down==0,'rsi']=100;f.loc[(up==0)&(down==0),'rsi']=50
    f['basis']=c.rolling(20).mean();f['lower']=f.basis-2*c.rolling(20).std(ddof=0)
    f['channel_high']=f.high.shift().rolling(20).max();f['channel_low']=f.low.shift().rolling(10).min()
    ready=np.arange(len(f))>=200
    f['entry_trend']=ready&(f.fast>f.slow)&(f.slow>f.regime)&(c>f.fast)&(c.shift()<=f.fast.shift())&(f.rsi>50)
    f['exit_trend']=(c<f.slow)&(c.shift()>=f.slow.shift())
    f['entry_reclaim']=ready&(c>f.regime)&(c.shift()<f.lower.shift())&(c>f.lower)&(f.rsi<50)
    f['exit_reclaim']=(c>f.basis)|(f.rsi>60)
    f['entry_breakout']=ready&(c>f.regime)&(c>f.channel_high)
    f['exit_breakout']=c<f.channel_low
    return f


def simulate(frame,rule,kind,start,end,stress=1):
    cash=10000.;position=None;pending=None;closing=False;trades=[];marks=[];stop_mult,target_mult=RULES[rule]
    fee=(.004 if kind=='crypto' else 0)*stress;slip=.0002*stress
    def exit_position(raw,ts,reason):
        nonlocal cash,position
        price=raw*(1-slip);proceeds=position['qty']*price;net=proceeds*(1-fee)-position['cost'];cash+=proceeds*(1-fee)
        trades.append({'entry_ts':position['ts'],'exit_ts':ts,'entry':position['entry'],'exit':price,'net_pnl':net,'reason':reason})
        position=None
    active=frame[(frame.ts>=start)&(frame.ts<end)]
    if active.empty:raise ValueError('No evaluation bars')
    for row in active.to_dict('records'):
        ts=int(row['ts'])
        if position and closing:exit_position(row['open'],ts,'signal');closing=False
        if pending and not position:
            elapsed=ts-pending['ts']
            if (kind!='crypto' or elapsed==3600000) and 0<elapsed<=4*86400000:
                entry=row['open']*(1+slip);budget=cash*.1;qty=budget/entry;cost=budget*(1+fee);cash-=cost
                position={'qty':qty,'cost':cost,'entry':entry,'ts':ts,'stop':entry-stop_mult*pending['atr'],'target':entry+target_mult*pending['atr']}
            pending=None
        if position:
            if row['open']<=position['stop']:exit_position(row['open'],ts,'gap_stop')
            elif row['low']<=position['stop']:exit_position(position['stop'],ts,'stop')
            elif row['high']>=position['target']:exit_position(position['target'],ts,'target')
        equity=cash+(position['qty']*row['close'] if position else 0);marks.append(equity)
        if position and row['exit_'+rule]:closing=True
        if not position and row['entry_'+rule] and math.isfinite(row['atr']):pending={'atr':row['atr'],'ts':ts}
    if position:exit_position(float(active.iloc[-1]['close']),int(active.iloc[-1]['ts']),'end_liquidation')
    marks.append(cash);curve=np.array([10000.,*marks]);peaks=np.maximum.accumulate(curve);dd=float(((peaks-curve)/peaks).max()*100)
    wins=sum(t['net_pnl']>0 for t in trades);profits=sum(max(t['net_pnl'],0) for t in trades);losses=-sum(min(t['net_pnl'],0) for t in trades)
    return {'return_pct':(cash/10000-1)*100,'max_drawdown_pct':dd,'trades':len(trades),'win_pct':wins/len(trades)*100 if trades else None,'profit_factor':profits/losses if losses else None,'final_equity':cash},trades


def ms(day):return int(pd.Timestamp(day,tz='UTC').timestamp()*1000)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--data',type=Path,required=True);parser.add_argument('--out',type=Path,default=ROOT/'research/pine_pack_v1/results');args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    plan_path=ROOT/'research/pine_pack_v1/plan.json';plan=json.loads(plan_path.read_text());manifest=json.loads((args.data/'manifest.json').read_text())
    summary={'run_at':datetime.now(timezone.utc).isoformat(),'plan_sha256':hashlib.sha256(plan_path.read_bytes()).hexdigest(),'source_retrieved_at':manifest.get('retrieved_at'),'pine_executed':False,'live_approved':False,'results':[],'sources':{}}
    ledger=[]
    for symbol in plan['symbols']:
        path=args.data/(symbol+'.json');raw=path.read_bytes();digest=hashlib.sha256(raw).hexdigest()
        if digest!=manifest['assets'][symbol]['sha256']:raise ValueError('Candle provenance mismatch: '+symbol)
        data=json.loads(raw);f=pd.DataFrame(data['bars']);f=f.sort_values('ts').reset_index(drop=True)
        if f.ts.duplicated().any() or not ((f.low>0)&(f.high>=f[['open','close']].max(axis=1))&(f.low<=f[['open','close']].min(axis=1))).all():raise ValueError('Invalid source candles')
        f=indicators(f);kind=data['kind'];summary['sources'][symbol]={'sha256':digest,'bars':len(f),'source':data.get('source'),'source_url':data.get('source_url'),'start':int(f.ts.min()),'end':int(f.ts.max())}
        for rule in RULES:
            for period,start,end in [('early',plan['early_start'],plan['later_start']),('later',plan['later_start'],plan['end_exclusive'])]:
                for stress in (1,2):
                    metrics,trades=simulate(f,rule,kind,ms(start),ms(end),stress)
                    summary['results'].append({'symbol':symbol,'rule':rule,'period':period,'stress':stress,**metrics})
                    for trade in trades:ledger.append({'symbol':symbol,'rule':rule,'period':period,'stress':stress,**trade})
    (args.out/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    with (args.out/'trades.csv').open('w') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(ledger[0]) if ledger else []);writer.writeheader();writer.writerows(ledger)
    for rule in RULES:
        rows=[r for r in summary['results'] if r['rule']==rule and r['period']=='later' and r['stress']==1]
        print(rule, ' | '.join(f"{r['symbol']}: {r['return_pct']:.2f}%, {r['trades']} trades, DD {r['max_drawdown_pct']:.2f}%" for r in rows))


if __name__=='__main__':main()
