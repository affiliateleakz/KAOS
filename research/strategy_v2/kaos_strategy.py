"""KAOS Structure v2: a market-neutral price-action research strategy.
Research/paper only. No broker connectors; not a claim of profitability.
Usage: python kaos_strategy.py candles.csv --fee-bps 5 --slippage-bps 2
CSV: time,open,high,low,close[,volume]. Sorted ascending, regular intervals.
"""
import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd

def features(raw):
    d=raw.copy().reset_index(drop=True)
    d.columns=[str(c).lower() for c in d.columns]
    required=['open','high','low','close']
    if not all(c in d for c in required): raise ValueError('Required: open high low close')
    for c in required: d[c]=pd.to_numeric(d[c],errors='raise')
    if (d[required].isna().any().any() or (d[required]<=0).any().any() or
        (d.high<d[['open','close','low']].max(axis=1)).any() or
        (d.low>d[['open','close','high']].min(axis=1)).any()):
        raise ValueError('Invalid OHLC')
    d['ema20']=d.close.ewm(span=20,adjust=False).mean()
    d['ema50']=d.close.ewm(span=50,adjust=False).mean()
    tr=pd.concat([(d.high-d.low), (d.high-d.close.shift()).abs(),(d.low-d.close.shift()).abs()],axis=1).max(axis=1)
    d['atr']=tr.ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    d['prior_high']=d.high.shift(1).rolling(20).max()
    d['prior_low']=d.low.shift(1).rolling(20).min()
    d['vol_base']=d.volume.shift(1).rolling(20).median() if 'volume' in d else np.nan
    return d

def generate(raw):
    """Signals only on closed bars. Two structural setups, same rules for all asset types."""
    d=features(raw)
    up=(d.ema20>d.ema50)&(d.ema20>d.ema20.shift(4))
    down=(d.ema20<d.ema50)&(d.ema20<d.ema20.shift(4))
    bullish=(d.close>d.open)&((d.close-d.open)>=0.45*(d.high-d.low))
    bearish=(d.close<d.open)&((d.open-d.close)>=0.45*(d.high-d.low))
    volok=(d.volume>=1.2*d.vol_base) if 'volume' in d else pd.Series(True,index=d.index)
    # Confirmed break of prior 20-bar structure with trend; require >0.15 ATR breakout.
    long_break=up&bullish&volok&(d.close>d.prior_high+0.15*d.atr)
    short_break=down&bearish&volok&(d.close<d.prior_low-0.15*d.atr)
    # Pullback touches EMA20 during previous 3 bars, then closes back through preceding bar high/low.
    touched_long=((d.low.shift(1)<=d.ema20.shift(1)+0.15*d.atr.shift(1)) |
                  (d.low.shift(2)<=d.ema20.shift(2)+0.15*d.atr.shift(2)) |
                  (d.low.shift(3)<=d.ema20.shift(3)+0.15*d.atr.shift(3)))
    touched_short=((d.high.shift(1)>=d.ema20.shift(1)-0.15*d.atr.shift(1)) |
                  (d.high.shift(2)>=d.ema20.shift(2)-0.15*d.atr.shift(2)) |
                  (d.high.shift(3)>=d.ema20.shift(3)-0.15*d.atr.shift(3)))
    long_pull=up&bullish&touched_long&(d.close>d.high.shift(1))&(d.close>d.ema20)&(d.close<=d.prior_high+0.5*d.atr)
    short_pull=down&bearish&touched_short&(d.close<d.low.shift(1))&(d.close<d.ema20)&(d.close>=d.prior_low-0.5*d.atr)
    # No trade if excess volatility or insufficient ATR/warmup.
    atr_ok=(d.atr>0)&((d.atr/d.close).between(0.00005,0.08))
    d['direction']=np.select([atr_ok&(long_break|long_pull),atr_ok&(short_break|short_pull)],[1,-1],default=0)
    d['setup']=np.select([atr_ok&long_break,atr_ok&short_break,atr_ok&long_pull,atr_ok&short_pull],['breakout_long','breakout_short','pullback_long','pullback_short'],default='none')
    d.loc[:55,['direction','setup']]=[0,'none']
    return d

def backtest(raw, fee_bps=5,slippage_bps=2,risk_fraction=0.005,max_bars=48,starting_cash=10000,allow_short=True):
    """Single position, next-open fill, stop-first ambiguity; costs as % of notional.
    Gap through stop exits at worse available open; overnight/liquidity gaps are still simplified.
    """
    if min(fee_bps,slippage_bps,risk_fraction,max_bars,starting_cash)<0 or risk_fraction>=1 or max_bars<1 or starting_cash<=0:
        raise ValueError('Invalid backtest parameters')
    d=generate(raw)
    cash=float(starting_cash); trades=[]; position=None
    fr=(fee_bps+slippage_bps)/10000
    for i in range(56,len(d)):
        bar=d.iloc[i]
        if position is None:
            prev=d.iloc[i-1]
            side=int(prev.direction)
            if side==0 or (side<0 and not allow_short): continue
            atr=float(prev.atr)
            if not np.isfinite(atr) or atr<=0: continue
            # Spread/slippage modeled adversarially for both entry and exit.
            entry=float(bar.open)*(1+side*slippage_bps/10000)
            stop=entry-side*1.5*atr
            target=entry+side*3.0*atr # 2R target
            if stop<=0: continue
            risk_budget=max(0,cash*risk_fraction)
            qty=min(risk_budget/(1.5*atr+2*entry*fr), cash/(entry*(1+fr)))
            if qty<=0: continue
            position={'index':i,'side':side,'entry':entry,'stop':stop,'target':target,'qty':qty,'setup':prev.setup,'cash_before':cash}
        # Important: entry candle is evaluated too. Conservative ordering.
        p=position
        if p is None: continue
        side=p['side']; stop=p['stop']; target=p['target']
        adverse_open=(side==1 and bar.open<=stop) or (side==-1 and bar.open>=stop)
        adverse_hit=(side==1 and bar.low<=stop) or (side==-1 and bar.high>=stop)
        target_hit=(side==1 and bar.high>=target) or (side==-1 and bar.low<=target)
        reason=None
        if adverse_open: exit_raw=float(bar.open); reason='stop_gap'
        elif adverse_hit: exit_raw=stop; reason='stop'
        elif target_hit: exit_raw=target; reason='target'
        elif i-p['index']+1>=max_bars: exit_raw=float(bar.close); reason='time'
        if reason:
            exit_price=exit_raw*(1-side*slippage_bps/10000)
            fees=(p['entry']+exit_price)*p['qty']*fee_bps/10000
            pnl=(exit_price-p['entry'])*side*p['qty']-fees
            cash+=pnl
            trades.append({'entry_row':p['index'],'exit_row':i,'side':'BUY' if side>0 else 'SELL',
                           'setup':p['setup'],'entry_price':p['entry'],'exit_price':exit_price,
                           'quantity':p['qty'],'fees':fees,'pnl':pnl,'cash_after':cash,'exit_reason':reason})
            position=None
    t=pd.DataFrame(trades)
    if t.empty: return d,t,{'trades':0,'net_pnl':0,'return_pct':0,'win_rate_pct':None,'max_closed_equity_drawdown_pct':0,'end_equity':starting_cash}
    eq=pd.concat([pd.Series([starting_cash]),t.cash_after],ignore_index=True)
    drawdown=(eq/eq.cummax()-1).min()*100
    summary={'trades':int(len(t)),'wins':int((t.pnl>0).sum()),'losses':int((t.pnl<0).sum()),
             'win_rate_pct':round(100*(t.pnl>0).mean(),3), 'net_pnl':round(float(t.pnl.sum()),2),
             'return_pct':round(100*(cash/starting_cash-1),3),'end_equity':round(cash,2),
             'max_closed_equity_drawdown_pct':round(float(drawdown),3),
             'profit_factor':round(float(t.loc[t.pnl>0,'pnl'].sum()/-t.loc[t.pnl<0,'pnl'].sum()),3) if (t.pnl<0).any() else None,
             'open_position_excluded':position is not None}
    return d,t,summary

def main():
    p=argparse.ArgumentParser();p.add_argument('csv');p.add_argument('--fee-bps',type=float,default=5)
    p.add_argument('--slippage-bps',type=float,default=2);p.add_argument('--max-bars',type=int,default=48)
    p.add_argument('--risk-fraction',type=float,default=0.005);p.add_argument('--no-shorts',action='store_true');p.add_argument('--out',default='kaos_backtest')
    a=p.parse_args();d,t,summary=backtest(pd.read_csv(a.csv),a.fee_bps,a.slippage_bps,a.risk_fraction,a.max_bars,allow_short=not a.no_shorts)
    Path(a.out).mkdir(parents=True,exist_ok=True)
    d.to_csv(Path(a.out)/'signals.csv',index=False)
    t.to_csv(Path(a.out)/'trades.csv',index=False)
    (Path(a.out)/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
if __name__=='__main__': main()
