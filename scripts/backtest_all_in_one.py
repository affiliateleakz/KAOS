"""No-order, cost-aware hourly replay of the frozen KAOS All-in-one Strategy."""
import argparse,csv,hashlib,importlib.util,json,math
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('kaos_all_in_one',ROOT/'research/all_in_one_v1/strategy.py')
strategy=importlib.util.module_from_spec(spec);spec.loader.exec_module(strategy)
DAY=86400000


def stamp(day):return int(datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp()*1000)


def usd_pnl(symbol,units,entry,exit,side):return units*side*(exit-entry)/(exit if symbol=='USDJPY=X' else 1)


def notional(symbol,units,price):return units if symbol=='USDJPY=X' else units*price


def fills(raw,side,cost,opening):return raw*(1+side*cost['adverse_bps_each_side']/10000*(1 if opening else -1))


def carry(symbol,p,ts,cost):return notional(symbol,p['units'],p['entry'])*cost['carry_bps_day']/10000*max(0,ts-p['entry_ts'])/DAY


def close_position(symbol,p,raw,ts,reason,equity,cost):
    price=fills(raw,p['side'],cost,False);fee=notional(symbol,p['units'],price)*cost['commission_bps_each_side']/10000;finance=carry(symbol,p,ts,cost)
    gross=usd_pnl(symbol,p['units'],p['entry'],price,p['side']);equity+=gross-fee-finance
    net=gross-fee-finance-p['entry_fee']+p['dividends']
    return equity,{**p,'exit_ts':int(ts),'exit':price,'exit_reason':reason,'exit_fee':fee,'financing':finance,'gross_price_pnl':gross,'net_pnl':net,'net_R':net/p['planned_risk']}


def drawdown(values):
    a=np.asarray(values,dtype=float);peak=np.maximum.accumulate(a);return float(np.max((peak-a)/peak)*100)


def backtest(record,frame,candidates,start,end,plan,multiplier=1):
    symbol=record['symbol'];kind=record['kind'];cost={k:v*multiplier if isinstance(v,(float,int)) else v for k,v in plan['costs'][kind].items()};initial=plan['capital_per_instrument'];equity=float(initial);position=None;trades=[];daily={};counts={'entry_signals':0,'gap_entries_cancelled':0,'entries_without_size':0,'ambiguous_stop_first':0};dividends=sorted(record.get('dividends',[]),key=lambda d:d['ts']);di=0;last=None
    rows=frame.to_dict('records')
    for i,row in enumerate(rows):
        ts=int(row['ts']);finish=int(row['end'])
        if ts<start or finish>end:continue
        while di<len(dividends) and dividends[di]['ts']<=ts:
            event=dividends[di]
            if position and position['entry_ts']<event['ts']:
                cash=position['units']*event['amount']*position['side'];equity+=cash;position['dividends']+=cash
            di+=1
        was_open=position is not None
        if position:
            gap_stop=row['open']<=position['stop'] if position['side']==1 else row['open']>=position['stop']
            gap_target=row['open']>=position['target'] if position['side']==1 else row['open']<=position['target']
            if gap_stop or gap_target:
                raw=row['open'] if gap_stop else position['target'];equity,t=close_position(symbol,position,raw,ts,'gap_stop' if gap_stop else 'gap_target',equity,cost);trades.append(t);position=None
        signal=candidates.get(i-1)
        if not was_open and position is None and signal:
            counts['entry_signals']+=1;side=signal['side'];stop=signal['stop']
            if row.get('quote_gap',False) or ts-signal['signal_ts']>4*DAY or abs(row['open']-signal['signal_close'])>.25*signal['atr']:
                counts['gap_entries_cancelled']+=1
            else:
                entry=fills(row['open'],side,cost,True);stop_fill=fills(stop,side,cost,False);distance=side*(entry-stop)
                if distance<=0:counts['gap_entries_cancelled']+=1
                else:
                    unit_fee=(notional(symbol,1,entry)+notional(symbol,1,stop_fill))*cost['commission_bps_each_side']/10000
                    risk_per_unit=-usd_pnl(symbol,1,entry,stop_fill,side)+unit_fee
                    if risk_per_unit<=0:raise ValueError('Invalid stop risk')
                    units=min(equity*plan['risk_fraction']/risk_per_unit,equity/(notional(symbol,1,entry)*(1+cost['commission_bps_each_side']/10000)))
                    units=math.floor(units) if kind in ('stocks','forex') else math.floor(units*1e8)/1e8
                    if units<=0:counts['entries_without_size']+=1
                    else:
                        fee=notional(symbol,units,entry)*cost['commission_bps_each_side']/10000;equity-=fee
                        position={'symbol':symbol,'kind':kind,'entry_ts':ts,'signal_ts':signal['signal_ts'],'side':side,'entry':entry,'units':units,'stop':stop,'target':entry+side*2*distance,'entry_fee':fee,'planned_risk':units*risk_per_unit,'dividends':0.}
        if position:
            hit_stop=row['low']<=position['stop'] if position['side']==1 else row['high']>=position['stop']
            hit_target=row['high']>=position['target'] if position['side']==1 else row['low']<=position['target']
            if hit_stop or hit_target:
                if hit_stop and hit_target:counts['ambiguous_stop_first']+=1
                equity,t=close_position(symbol,position,position['stop'] if hit_stop else position['target'],finish,'stop_first_ambiguous' if hit_stop and hit_target else 'stop' if hit_stop else 'target',equity,cost);trades.append(t);position=None
        nav=equity
        if position:
            liquidation=fills(row['close'],position['side'],cost,False);fee=notional(symbol,position['units'],liquidation)*cost['commission_bps_each_side']/10000
            nav+=usd_pnl(symbol,position['units'],position['entry'],liquidation,position['side'])-fee-carry(symbol,position,finish,cost)
        daily[datetime.fromtimestamp((finish-1)/1000,timezone.utc).strftime('%Y-%m-%d')]=nav;last=row
    if position and last:
        equity,t=close_position(symbol,position,last['close'],last['end'],'end_of_test',equity,cost);trades.append(t);position=None
        daily[datetime.fromtimestamp((last['end']-1)/1000,timezone.utc).strftime('%Y-%m-%d')]=equity
    if not math.isclose(equity,initial+sum(t['net_pnl'] for t in trades),abs_tol=1e-7):raise AssertionError('Equity ledger does not reconcile')
    wins=sum(t['net_pnl']>0 for t in trades);losses=sum(t['net_pnl']<0 for t in trades);profits=sum(max(0,t['net_pnl']) for t in trades);loss=sum(max(0,-t['net_pnl']) for t in trades)
    summary={'symbol':symbol,'kind':kind,'trades':len(trades),'wins':wins,'losses':losses,'win_rate':wins/len(trades) if trades else None,'profit_factor':profits/loss if loss else None,'net_R':sum(t['net_R'] for t in trades),'net_pnl':equity-initial,'return_pct':(equity/initial-1)*100,'max_daily_drawdown_pct':drawdown([initial]+list(daily.values())),'ending_equity':equity,'counts':counts,'commission_paid':sum(t['entry_fee']+t['exit_fee'] for t in trades),'financing_paid':sum(t['financing'] for t in trades),'dividends_received':sum(t['dividends'] for t in trades)}
    return summary,trades,daily


def portfolio(summaries,dailies,start,end,capital):
    dates=pd.date_range(start=pd.Timestamp(start,unit='ms',tz='UTC').normalize(),end=pd.Timestamp(end-1,unit='ms',tz='UTC').normalize(),freq='D').strftime('%Y-%m-%d')
    series=[pd.Series(daily,dtype=float).reindex(dates).ffill().fillna(capital) for daily in dailies]
    nav=sum(series);initial=capital*len(series);daily_returns=nav.pct_change().fillna(nav.iloc[0]/initial-1).to_numpy();weekly=np.array([np.log1p(daily_returns[i:i+7]).sum() for i in range(0,len(daily_returns),7)])
    rng=np.random.default_rng(47);boot=np.expm1(rng.choice(weekly,size=(5000,len(weekly)),replace=True).sum(axis=1))*100
    return {'instruments':len(summaries),'initial_equity':initial,'ending_equity':float(nav.iloc[-1]),'return_pct':float((nav.iloc[-1]/initial-1)*100),'max_daily_drawdown_pct':drawdown([initial]+nav.tolist()),'trades':sum(s['trades'] for s in summaries),'net_R_sum':sum(s['net_R'] for s in summaries),'weekly_block_bootstrap_return95':[float(np.quantile(boot,.025)),float(np.quantile(boot,.975))],'daily_nav':{str(k):float(v) for k,v in nav.items()}}


def main():
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    plan_path=ROOT/'research/all_in_one_v1/plan.json';plan=json.loads(plan_path.read_text());manifest=json.loads((a.data/'manifest.json').read_text());instruments=[];quality={}
    for symbol,info in manifest['assets'].items():
        path=a.data/info['file'];raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=info['sha256']:raise ValueError('Input hash mismatch')
        record=json.loads(raw);frame,q=strategy.indicators(record['bars'],record['kind']);candidates=strategy.signals(frame,record['kind']);quality[symbol]={**q,'signals':len(candidates)};instruments.append((record,frame,candidates))
    report={'strategy':plan['name'],'plan_sha256':hashlib.sha256(plan_path.read_bytes()).hexdigest(),'strategy_sha256':hashlib.sha256(Path(strategy.__file__).read_bytes()).hexdigest(),'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'source_manifest_sha256':hashlib.sha256((a.data/'manifest.json').read_bytes()).hexdigest(),'quality':quality,'periods':{},'live_approved':False}
    all_trades=[]
    periods=[('development',plan['data_start'],plan['evaluation_start'],1),('later_evaluation',plan['evaluation_start'],plan['data_end_exclusive'],1),('later_double_costs',plan['evaluation_start'],plan['data_end_exclusive'],2)]
    for name,start_date,end_date,multiplier in periods:
        start,end=stamp(start_date),stamp(end_date);summaries=[];daily=[];kinds={}
        for record,frame,candidates in instruments:
            summary,rows,nav=backtest(record,frame,candidates,start,end,plan,multiplier);summaries.append(summary);daily.append(nav);kinds.setdefault(record['kind'],[]).append((summary,nav));all_trades.extend({'period':name,**r} for r in rows)
        report['periods'][name]={'start':start_date,'end_exclusive':end_date,'cost_multiplier':multiplier,'instruments':summaries,'portfolio':portfolio(summaries,daily,start,end,plan['capital_per_instrument']),'classes':{kind:portfolio([s for s,_ in items],[n for _,n in items],start,end,plan['capital_per_instrument']) for kind,items in kinds.items()}}
        print(name,{k:round(v['return_pct'],4) for k,v in report['periods'][name]['classes'].items()},flush=True)
    result=a.out/'summary.json';result.write_text(json.dumps(report,indent=2)+'\n')
    with (a.out/'trades.csv').open('w') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(all_trades[0]) if all_trades else ['period'],lineterminator='\n');writer.writeheader();writer.writerows(all_trades)
    print('Backtest complete; no live approval',flush=True)

if __name__=='__main__':main()
