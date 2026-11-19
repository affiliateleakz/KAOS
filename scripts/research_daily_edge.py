"""Cost-aware bounded selection, one frozen class/strategy choice, fresh historical final."""
import argparse,csv,hashlib,importlib.util,json,math
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
strategy=module('daily_rules',ROOT/'research/daily_edge_v1/strategy.py')
utils=module('execution_utils',ROOT/'scripts/backtest_all_in_one.py')
DAY=86400000


def stamp(day):return int(datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp()*1000)


def replay(record,frame,name,start,end,plan,multiplier=1,benchmark=False):
    symbol=record['symbol'];kind=record['kind'];cost={k:v*multiplier for k,v in plan['costs'][kind].items()};initial=plan['capital_per_instrument'];equity=float(initial);position=None;pending=0;exit_pending=False;trades=[];daily={};exposure=[];divs=sorted(record.get('dividends',[]),key=lambda d:d['ts']);di=0;last=None;had_benchmark_entry=False
    for i,row in frame.iterrows():
        ts=int(row.ts)
        if ts<start or ts>=end:continue
        while di<len(divs) and divs[di]['ts']<=ts:
            event=divs[di]
            if position and position['entry_ts']<event['ts']:
                cash=position['units']*event['amount']*position['side'];equity+=cash;position['dividends']+=cash
            di+=1
        had=position is not None
        if position:
            gap_stop=not benchmark and (row.open<=position['stop'] if position['side']==1 else row.open>=position['stop'])
            if gap_stop or exit_pending:
                equity,t=utils.close_position(symbol,position,row.open,ts,'gap_stop' if gap_stop else 'rule_exit',equity,cost);trades.append(t);position=None
        if benchmark and not had_benchmark_entry:pending=1
        if not had and position is None and pending and (benchmark or i>0 and np.isfinite(frame.iloc[i-1].atr)):
            side=pending;entry=utils.fills(row.open,side,cost,True);atr=float(frame.iloc[i-1].atr) if i else 1.;distance=(2 if name in ('rsi2_bull_pullback','range_fade') else 3)*atr;stop=entry-side*distance;stop_fill=utils.fills(stop,side,cost,False)
            if stop>0:
                unit_fee=(utils.notional(symbol,1,entry)+utils.notional(symbol,1,stop_fill))*cost['commission_bps_each_side']/10000;risk=-utils.usd_pnl(symbol,1,entry,stop_fill,side)+unit_fee
                cap=equity/(utils.notional(symbol,1,entry)*(1+cost['commission_bps_each_side']/10000));units=cap if benchmark else min(cap,equity*plan['risk_fraction']/risk);units=math.floor(units*1e8)/1e8
                if units>0:
                    fee=utils.notional(symbol,units,entry)*cost['commission_bps_each_side']/10000;equity-=fee;position={'symbol':symbol,'kind':kind,'entry_ts':ts,'signal_ts':int(frame.iloc[i-1].ts) if i else ts,'side':side,'entry':entry,'units':units,'stop':stop,'entry_fee':fee,'planned_risk':max(1e-12,units*risk),'dividends':0.,'held':0};had_benchmark_entry=True
        pending=0;exit_pending=False
        # Daily close is an observation time, not an assumed exact intraday stop timestamp.
        close_ts=min(end-1,ts+DAY-1)
        if position and not benchmark:
            stop_hit=row.low<=position['stop'] if position['side']==1 else row.high>=position['stop']
            if stop_hit:
                equity,t=utils.close_position(symbol,position,position['stop'],close_ts,'protective_stop',equity,cost);trades.append(t);position=None
        if position:position['held']+=1
        if not benchmark:
            desired,exit_pending=strategy.decision(row,name,kind,position['side'] if position else 0,position['held'] if position else 0)
            if position is None:pending=desired
            if position and name=='chandelier22_3atr':
                trail=row.highest22-3*row.atr if position['side']==1 else row.lowest22+3*row.atr
                position['stop']=max(position['stop'],trail) if position['side']==1 else min(position['stop'],trail)
        nav=equity;notional=0
        if position:
            exit=utils.fills(row.close,position['side'],cost,False);fee=utils.notional(symbol,position['units'],exit)*cost['commission_bps_each_side']/10000
            nav+=utils.usd_pnl(symbol,position['units'],position['entry'],exit,position['side'])-fee-utils.carry(symbol,position,close_ts,cost);notional=utils.notional(symbol,position['units'],row.close)
        date=datetime.fromtimestamp(ts/1000,timezone.utc).strftime('%Y-%m-%d');daily[date]=nav;exposure.append(notional/nav if nav>0 else 0);last=(row,close_ts,date)
    if position and last:
        equity,t=utils.close_position(symbol,position,last[0].close,last[1],'end_of_test',equity,cost);trades.append(t);daily[last[2]]=equity
    if not math.isclose(equity,initial+sum(t['net_pnl'] for t in trades),abs_tol=1e-6):raise AssertionError('Cash ledger mismatch')
    wins=sum(t['net_pnl']>0 for t in trades);profit=sum(max(0,t['net_pnl']) for t in trades);loss=sum(max(0,-t['net_pnl']) for t in trades)
    summary={'symbol':symbol,'trades':len(trades),'wins':wins,'win_rate':wins/len(trades) if trades else None,'return_pct':(equity/initial-1)*100,'profit_factor':profit/loss if loss else None,'max_daily_drawdown_pct':utils.drawdown([initial]+list(daily.values())),'average_observed_notional_exposure':float(np.mean(exposure)) if exposure else 0,'net_pnl':equity-initial,'net_R':sum(t['net_R'] for t in trades)}
    return summary,trades,daily


def group(records,frames,kind,name,start,end,plan,multiplier=1,benchmark=False):
    summaries=[];dailies=[];rows=[]
    for record in records:
        if record['kind']!=kind:continue
        s,t,d=replay(record,frames[record['symbol']],name,start,end,plan,multiplier,benchmark);summaries.append(s);dailies.append(d);rows.extend(t)
    p=utils.portfolio(summaries,dailies,start,end,plan['capital_per_instrument']);p['instruments']=summaries;p['average_notional_exposure']=float(np.mean([s['average_observed_notional_exposure'] for s in summaries]));return p,rows


def write(path,data):path.write_text(json.dumps(data,indent=2)+'\n')


def main():
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    path=ROOT/'research/daily_edge_v1/plan.json';plan=json.loads(path.read_text());manifest=json.loads((a.data/'manifest.json').read_text());records=[];frames={}
    for info in manifest['assets'].values():
        raw=(a.data/info['file']).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=info['sha256']:raise ValueError('Data checksum mismatch')
        record=json.loads(raw);records.append(record);frames[record['symbol']]=strategy.indicators(record['bars'])
    write(a.out/'provenance.json',{'plan_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'strategy_sha256':hashlib.sha256(Path(strategy.__file__).read_bytes()).hexdigest(),'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'input_manifest_sha256':hashlib.sha256((a.data/'manifest.json').read_bytes()).hexdigest(),'live_approved':False})
    start,cut,end=map(stamp,(plan['validation_start'],plan['final_start'],plan['end_exclusive']));validation=[]
    for kind in plan['universe']:
        for name in strategy.CANDIDATES:
            base,_=group(records,frames,kind,name,start,cut,plan);stress,_=group(records,frames,kind,name,start,cut,plan,2)
            eligible=base['trades']>=40 and base['return_pct']>0 and stress['return_pct']>0 and base['max_daily_drawdown_pct']<=15
            validation.append({'kind':kind,'strategy':name,'eligible':eligible,'score':base['return_pct']/max(2,base['max_daily_drawdown_pct']),'base':base,'double_costs':stress});print('validation',kind,name,round(base['return_pct'],3),eligible,flush=True)
    write(a.out/'validation.json',validation);eligible=[v for v in validation if v['eligible']];chosen=max(eligible,key=lambda r:r['score']) if eligible else None
    selection={'chosen':{'kind':chosen['kind'],'strategy':chosen['strategy']} if chosen else None,'trials':len(validation),'eligible':len(eligible),'frozen_before_final':True};write(a.out/'selection.json',selection);print(json.dumps(selection),flush=True)
    result={'state':'no_validation_candidate','selection':selection['chosen'],'live_approved':False,'cash_benchmark_return_pct':0}
    if chosen:
        kind,name=chosen['kind'],chosen['strategy'];final,trades=group(records,frames,kind,name,cut,end,plan);stress,_=group(records,frames,kind,name,cut,end,plan,2);benchmark,_=group(records,frames,kind,name,cut,end,plan,benchmark=True)
        passed=final['trades']>=40 and final['return_pct']>0 and stress['return_pct']>0 and final['max_daily_drawdown_pct']<=15 and final['weekly_block_bootstrap_return95'][0]>0
        result.update(state='historically_positive_candidate_requires_forward_test' if passed else 'failed_final_gate',final=final,double_costs=stress,buy_hold=benchmark)
        with (a.out/'final_trades.csv').open('w') as file:
            writer=csv.DictWriter(file,fieldnames=list(trades[0]) if trades else ['symbol'],lineterminator='\n');writer.writeheader();writer.writerows(trades)
    write(a.out/'result.json',result);print(json.dumps({k:v for k,v in result.items() if k not in ('final','double_costs','buy_hold')}),flush=True)

if __name__=='__main__':main()
