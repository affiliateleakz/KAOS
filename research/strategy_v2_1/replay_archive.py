"""Reproduce exploratory KAOS v2.1 OTC archived candle replay. Not market validation."""
import json, argparse
from pathlib import Path
import pandas as pd
from kaos_strategy import backtest

def contiguous_runs(asset):
    d=pd.DataFrame(asset)
    d=d.rename(columns={'ts':'time'}).sort_values('time').drop_duplicates('time')
    d=d[['time','open','high','low','close']]
    valid=(d.time.diff().fillna(5000)==5000)
    for _,sub in d.groupby((~valid).cumsum()):
        if len(sub)>=100: yield sub.reset_index(drop=True)

def run(path,out):
    data=json.load(open(path))['rawCandleHistory']['byAsset']
    results=[]
    for asset,candles in data.items():
        for timeframe in [5,60]:
            for runid,run in enumerate(contiguous_runs(candles)):
                if timeframe==60:
                    run=run.copy();run['bucket']=(run.time//60000)
                    a=run.groupby('bucket').agg(time=('time','min'),open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last'),n=('close','size'))
                    # Only complete 12x5s bars, then split if any missing buckets.
                    a=a[a.n==12].reset_index(drop=True)
                    groups=[g for _,g in a.groupby((a.time.diff().fillna(60000)!=60000).cumsum())]
                else:groups=[run]
                for g in groups:
                    if len(g)<115:continue
                    # v2 is not short contract settlement; fees illustrative, 2 scenarios.
                    for fee in (0,10):
                        _,tr,s=backtest(g,fee_bps=fee,slippage_bps=2,allow_short=True)
                        results.append(dict(asset=asset,tf_seconds=timeframe,run=runid,fee_bps=fee,rows=len(g),**s))
    out=Path(out);out.mkdir(exist_ok=True,parents=True)
    df=pd.DataFrame(results);df.to_csv(out/'segment_results.csv',index=False)
    aggregated=[]
    for (tf,fee),g in df.groupby(['tf_seconds','fee_bps']):
        # Each run begins at 10k -> weighted aggregate trade P&L and trade wins, NOT portfolio equity.
        aggregated.append(dict(tf_seconds=int(tf),fee_bps=int(fee),market_segments=int(len(g)),markets=int(g.asset.nunique()),trades=int(g.trades.sum()),wins=int(g.wins.fillna(0).sum()),losses=int(g.losses.fillna(0).sum()),net_sim_pnl=float(g.net_pnl.sum()),win_rate_pct=round(100*g.wins.fillna(0).sum()/g.trades.sum(),2) if g.trades.sum() else None))
    (out/'summary.json').write_text(json.dumps({'source':'KAOS archive 2026-10-03 OTC 5s, not stock/crypto/forex validation','aggregate':aggregated},indent=2))
    print(json.dumps(aggregated,indent=2))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('archive');p.add_argument('--out',default='audit');a=p.parse_args();run(a.archive,a.out)
