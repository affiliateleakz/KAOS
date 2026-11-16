"""Strict closed-candle replay of the actual SR1.1 KAOS Strategy; never places orders."""
import csv
import hashlib
import json
import math
from pathlib import Path
import kaos_signature as strategy


def wilson(wins, total):
    if not total: return 0.0
    p=wins/total; z=1.96; d=1+z*z/total
    return (p+z*z/(2*total)-z*math.sqrt(p*(1-p)/total+z*z/(4*total*total)))/d


def normalized(rows):
    result={}
    for row in rows:
        ts=int(row['ts']); values=[float(row[k]) for k in ('open','high','low','close')]
        o,h,l,c=values
        if ts<=0 or ts%5000 or not all(math.isfinite(v) and v>0 for v in values) or not l<=min(o,c)<=max(o,c)<=h:
            raise ValueError('Require aligned, positive, finite five-second OHLC bars')
        bar=dict(zip(('open','high','low','close'),values),ts=ts)
        if ts in result and result[ts]!=bar: raise ValueError('Conflicting duplicate candles')
        result[ts]=bar
    return sorted(result.values(),key=lambda r:r['ts'])


def replay(markets, payout=.8, holdout=.25, provenance=None):
    if not 0<payout<=1 or not .1<=holdout<=.5: raise ValueError('Invalid payout or holdout')
    clean={symbol:normalized(rows) for symbol,rows in markets.items()}
    timeline=sorted({r['ts'] for rows in clean.values() for r in rows})
    if len(timeline)<100: raise ValueError('Need at least 100 distinct five-second observations')
    cutoff=timeline[int(len(timeline)*(1-holdout))]
    trades=[]; gaps=0; segments=0
    for symbol,rows in sorted(clean.items()):
        parts=[];part=[]
        for row in rows:
            if part and row['ts']!=part[-1]['ts']+5000:
                parts.append(part);part=[];gaps+=1
            part.append(row)
        if part:parts.append(part)
        for part in parts:
            segments+=1;by_ts={r['ts']:r for r in part};busy=0
            for i in range(49,len(part)-1):
                signal=strategy.evaluate(part[max(0,i-4999):i+1])
                entry_ts=part[i]['ts']+5000
                expiry=int(signal['expiration'].rstrip('s')) if signal else 0
                exit_ts=entry_ts+expiry*1000
                if not signal or entry_ts<busy or exit_ts not in by_ts:continue
                entry=by_ts[entry_ts]['open'];settlement=by_ts[exit_ts]['open'];side=1 if signal['direction']=='BUY' else -1
                result='TIE' if settlement==entry else 'WIN' if (settlement-entry)*side>0 else 'LOSS'
                trades.append({'symbol':symbol,'signal_ts':part[i]['ts'],'entry_ts':entry_ts,'exit_ts':exit_ts,'direction':signal['direction'],'engine':signal['engine'],'entry':entry,'settlement':settlement,'result':result,'unit_pnl':payout if result=='WIN' else -1 if result=='LOSS' else 0,'period':'holdout' if entry_ts>=cutoff else 'development'})
                busy=exit_ts
    def metrics(rows):
        w=sum(r['result']=='WIN' for r in rows);l=sum(r['result']=='LOSS' for r in rows);n=w+l
        return {'trades':len(rows),'wins':w,'losses':l,'ties':len(rows)-n,'win_rate':w/n if n else None,'wilson_lower_95':wilson(w,n),'unit_pnl':round(sum(r['unit_pnl'] for r in rows),4),'break_even_win_rate':1/(1+payout),'assumed_binary_payout':payout}
    held=metrics([r for r in trades if r['period']=='holdout']);full=metrics(trades)
    passed=held['wins']+held['losses']>=100 and held['wilson_lower_95']>held['break_even_win_rate']
    digest=hashlib.sha256(json.dumps(clean,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return {'strategy':'KAOS Strategy','engine':'SUPPORT_RESISTANCE','version':strategy.CFG['version'],'parameters':strategy.CFG,'strategy_sha256':hashlib.sha256(Path(strategy.__file__).read_bytes()).hexdigest(),'data_sha256':digest,'source':provenance or 'user-supplied candles','candles':sum(map(len,clean.values())),'markets':len(clean),'segments':segments,'gaps':gaps,'start_ts':timeline[0],'end_ts':timeline[-1],'holdout_start_ts':cutoff,'full':full,'holdout':held,'research_gate':'passed_historical_gate' if passed else 'insufficient_samples' if held['trades']<100 else 'failed_historical_gate','broker_execution_verified':False,'live_approved':False,'limitations':['Next-candle open entry; exact strategy-selected 15/20/25-second later open settlement proxy.','Binary payout is an assumption, not an observed broker payout.','Market-specific spreads, rejected orders and latency are not modeled.','Historical replay is not an untouched future validation or a profitability guarantee.'],'trades':sorted(trades,key=lambda r:(r['entry_ts'],r['symbol']))}


def main():
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('input');p.add_argument('--out',required=True);p.add_argument('--source',default='user-supplied candles');args=p.parse_args()
    raw=json.loads(Path(args.input).read_text());markets=raw.get('markets',raw.get('rawCandleHistory',{}).get('byAsset',{}))
    report=replay(markets,provenance=args.source);out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    rows=report.pop('trades');(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    with (out/'trades.csv').open('w') as f:
        writer=csv.DictWriter(f,lineterminator='\n',fieldnames=list(rows[0]) if rows else ['symbol','entry_ts','result']);writer.writeheader();writer.writerows(rows)
    print(json.dumps(report['holdout']));print(report['research_gate'])

if __name__=='__main__':main()
