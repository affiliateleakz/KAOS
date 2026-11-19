"""Three frozen session hypotheses, using actual calendar and complete source quotes."""
import argparse,csv,hashlib,json
from pathlib import Path
import numpy as np
import pandas as pd
import backtest_video_strategies as common
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'research/strategy_catalog_v1';HOUR=3600000


def dump(name,value):(OUT/name).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')

def full_sessions(record,raw):
    periods=raw['chart']['result'][0]['meta'].get('tradingPeriods',[])
    if isinstance(periods,dict):periods=periods.get('regular',[])
    calendar=sorted({(int(p['start'])*1000,int(p['end'])*1000) for day in periods for p in day})
    if not calendar:raise ValueError('No original exchange-session calendar')
    grouped={}
    for b in record['bars']:grouped.setdefault((b['session_start'],b['session_end']),[]).append(b)
    if not set(grouped).issubset(set(calendar)):raise ValueError('Quote session missing from source calendar')
    complete={};incomplete=0
    for start,end in calendar:
        rows=sorted(grouped.get((start,end),[]),key=lambda r:r['ts'])
        if not rows or [b['ts'] for b in rows]!=list(range(start,end,HOUR)) or any(b['end']!=min(b['ts']+HOUR,end) for b in rows):incomplete+=1;continue
        if any(not np.isfinite([b[k] for k in ['open','high','low','close']]).all() or not 0<b['low']<=min(b['open'],b['close'])<=max(b['open'],b['close'])<=b['high'] for b in rows):raise ValueError('Invalid quote')
        complete[start]=rows
    return calendar,complete,{'calendar_sessions':len(calendar),'complete_sessions':len(complete),'incomplete_or_missing_sessions':incomplete}


def cash_dividends(dividends,entry,exit):return sum(d['amount'] for d in dividends if entry<d['ts']<=exit)


def normalized_trade(asset,name,entry_ts,exit_ts,entry,exit,slip,reason,dividend=0.):
    paid=entry*(1+slip);received=exit*(1-slip)
    return {'asset':asset,'strategy':name,'entry':int(entry_ts),'exit':int(exit_ts),'entryPrice':paid,'exitPrice':received,'netBps':(received-paid+dividend)/paid*10000,'dividendPerUnit':dividend,'reason':reason,'executionEnabled':False}


def intraday(asset,name,rows,previous=None,stress=False):
    if len(rows)<3 or rows[0]['end']-rows[0]['ts']!=HOUR:return None
    first=rows[0];entry_i=None;previous_close=None
    if name=='opening_range_60':
        for i in range(1,len(rows)-1):
            if rows[i]['close']>first['high']:entry_i=i+1;break
    elif name=='gap_fade_60':
        if not previous:return None
        previous_close=previous[-1]['close'];gap=first['open']/previous_close-1
        if not -.02<=gap<=-.005 or first['close']<=first['open'] or first['close']>=previous_close:return None
        entry_i=1
    elif name=='intraday_control':entry_i=1
    else:raise ValueError('Unknown intraday hypothesis')
    if entry_i is None:return None
    entry_i+=int(stress)
    if entry_i>=len(rows) or rows[-1]['end']-rows[entry_i]['ts']<HOUR:return None
    entry=float(rows[entry_i]['open']);stop=float(first['low']);target=None
    if name!='intraday_control':
        if entry<=stop:return None
        target=entry+2*(entry-stop) if name=='opening_range_60' else previous_close
        if target<=entry or (target-entry)/entry<.001:return None #5times base2bps roundtrip, unchanged under stress.
    exit=float(rows[-1]['close']);exit_ts=rows[-1]['end'];reason='session_close'
    if target is not None:
        for bar in rows[entry_i:]:
            if bar['open']<=stop:exit=float(bar['open']);exit_ts=bar['end'];reason='stop_gap';break
            if bar['open']>=target:exit=target;exit_ts=bar['end'];reason='target';break
            if bar['low']<=stop:exit=stop;exit_ts=bar['end'];reason='stop';break
            if bar['high']>=target:exit=target;exit_ts=bar['end'];reason='target';break
    return normalized_trade(asset,name,rows[entry_i]['ts'],exit_ts,entry,exit,.0002 if stress else .0001,reason)


def overnight(asset,rows,next_rows,dividends,stress=False):
    entry=rows[-1];exit=next_rows[0]
    return normalized_trade(asset,'overnight_control',entry['end'],exit['ts'],entry['close'],exit['open'],.0002 if stress else .0001,'next_session_open',cash_dividends(dividends,entry['end'],exit['ts']))


def metrics(rows):
    pnl=np.array([r['netBps'] for r in rows]);gain=float(pnl[pnl>0].sum());loss=float(-pnl[pnl<0].sum());assets={};weeks={}
    for r in rows:
        assets[r['asset']]=assets.get(r['asset'],0)+r['netBps'];week=(r['entry']+3*86400000)//(7*86400000);weeks[week]=weeks.get(week,0)+r['netBps']
    lower=None
    if len(weeks)>1:
        values=np.array([weeks[k] for k in sorted(weeks)]);rng=np.random.default_rng(719);means=rng.choice(values,(5000,len(values)),replace=True).mean(1);lower=float(np.quantile(means,.05/3))
    return {'trades':len(rows),'days':len(set(r['entry']//86400000 for r in rows)),'meanNetBps':float(pnl.mean()) if len(pnl) else None,'profitFactor':gain/loss if loss else None,'profitableTradeRate':float((pnl>0).mean()) if len(pnl) else None,'weeklyLowerMeanBpsSum':lower,'assetSumBps':assets,'notPortfolioROI':True}


def gate(m,s):return bool(m['trades']>=100 and m['days']>=60 and m['profitFactor'] is not None and m['profitFactor']>=1.1 and sum(x>0 for x in m['assetSumBps'].values())>=5 and m['weeklyLowerMeanBpsSum'] is not None and m['weeklyLowerMeanBpsSum']>0 and s['meanNetBps'] is not None and s['meanNetBps']>0)


def main():
    p=argparse.ArgumentParser();p.add_argument('--markets',type=Path,required=True);p.add_argument('--market-cache',type=Path,required=True);p.add_argument('--equities',type=Path,required=True);p.add_argument('--equity-cache',type=Path,required=True);args=p.parse_args();plan=json.loads((OUT/'stock_sessions_plan.json').read_text());loaded={};provenance={}
    for symbol in plan['assets']:
        etf=symbol in ['SPY','QQQ','IWM','DIA'];directory=args.markets if etf else args.equities;manifest=json.loads((directory/'manifest.json').read_text());meta=manifest['assets'][symbol];file=directory/meta['file']
        if hashlib.sha256(file.read_bytes()).hexdigest()!=meta['sha256']:raise ValueError('Normalized snapshot checksum mismatch')
        record=json.loads(file.read_text());raw_path=(args.market_cache/(symbol+'.yahoo.json')) if etf else args.equity_cache/(symbol+'.json');raw_bytes=raw_path.read_bytes()
        if hashlib.sha256(raw_bytes).hexdigest()!=record['source_sha256']:raise ValueError('Original calendar/source checksum mismatch')
        calendar,sessions,counts=full_sessions(record,json.loads(raw_bytes));loaded[symbol]=(record,calendar,sessions);provenance[symbol]={'normalized_sha256':meta['sha256'],'original_sha256':record['source_sha256'],**counts}
    results={};allrows=[]
    for year,dates in plan['periods'].items():
        start,end=map(common.stamp,dates);trades={name:{'base':[],'stress':[]} for name in ['opening_range_60','gap_fade_60','overnight_control','intraday_control','buy_hold_daily_control']}
        for asset,(record,calendar,sessions) in loaded.items():
            for i,(begin,finish) in enumerate(calendar):
                if not start<=begin<end or begin not in sessions:continue
                rows=sessions[begin];previous=sessions.get(calendar[i-1][0]) if i else None
                for name in ['opening_range_60','gap_fade_60','intraday_control']:
                    for mode,stress in [('base',False),('stress',True)]:
                        trade=intraday(asset,name,rows,previous,stress)
                        if trade and trade['exit']<end:trades[name][mode].append(trade)
                if i+1<len(calendar) and calendar[i+1][0] in sessions:
                    next_rows=sessions[calendar[i+1][0]]
                    if next_rows[0]['ts']<end:
                        for mode,stress in [('base',False),('stress',True)]:trades['overnight_control'][mode].append(overnight(asset,rows,next_rows,record.get('dividends',[]),stress))
                if previous and previous[-1]['end']>=start:
                    before=previous[-1];last=rows[-1];d=cash_dividends(record.get('dividends',[]),before['end'],last['end']);trade=normalized_trade(asset,'buy_hold_daily_control',before['end'],last['end'],before['close'],last['close'],0.,'daily_mark',d)
                    trades['buy_hold_daily_control']['base'].append(trade);trades['buy_hold_daily_control']['stress'].append(trade)
        results[year]={}
        for name,versions in trades.items():
            r={mode:metrics(rows) for mode,rows in versions.items()};r['descriptive_gate']=gate(r['base'],r['stress']) if name in plan['rules'] else None;results[year][name]=r
            print(year,name,'n',r['base']['trades'],'meanbps',r['base']['meanNetBps'],'PF',r['base']['profitFactor'],'gate',r['descriptive_gate'],flush=True)
            for mode,rows in versions.items():allrows.extend({'period':year,'scenario':mode,**row} for row in rows)
    dump('stock_sessions_results.json',results);dump('stock_sessions_provenance.json',{'source':provenance,'plan_sha256':hashlib.sha256((OUT/'stock_sessions_plan.json').read_bytes()).hexdigest(),'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'independent_new_market_regime':False,'production_release':False})
    with (OUT/'stock_sessions_trades.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(allrows[0]),lineterminator='\n');w.writeheader();w.writerows(allrows)
if __name__=='__main__':main()
