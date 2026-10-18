"""Research-only CSV reader and next-open candle replay. Options and binary contracts excluded."""
import csv
from .core import Bar,Quote,PaperBroker,RiskGuard,ENGINES

def load_csv(path):
    with open(path,newline='',encoding='utf-8-sig') as f:
        r=csv.DictReader(f)
        bars=[Bar(x.get('time',x.get('timestamp','')),*(float(x[k]) for k in ['open','high','low','close']),float(x.get('volume') or 0)) for x in r]
    if not bars:raise ValueError('empty data')
    return bars

def replay(engine,symbol,bars,fee_bps=10,slippage_bps=2):
    if engine not in ('crypto','stock','forex'):raise ValueError('replay engine unsupported')
    risk=RiskGuard();broker=PaperBroker(risk,fee_bps,slippage_bps)
    # Signal at close of bar i-1; fill at bar i open, not signal candle close.
    # Entry bar is also checked; if stop and target touch, stop wins.
    for i in range(35,len(bars)):
        b=bars[i]
        p=broker.positions.get(symbol)
        if p:
            # Exit at open first on a price gap through stop/target, else conservative intrabar stop before target.
            side=p['direction']; stop=p['stop'];target=p['target'];reason=None;fill=None
            if side=='BUY':
                if b.open<=stop: fill=b.open;reason='gap_stop'
                elif target is not None and b.open>=target: fill=b.open;reason='gap_target'
                elif b.low<=stop:fill=stop;reason='stop'
                elif target is not None and b.high>=target:fill=target;reason='target'
            else:
                if b.open>=stop:fill=b.open;reason='gap_stop'
                elif target is not None and b.open<=target:fill=b.open;reason='gap_target'
                elif b.high>=stop:fill=stop;reason='stop'
                elif target is not None and b.low<=target:fill=target;reason='target'
            if fill is not None:broker.exit(symbol,Quote(fill,fill),reason)
        # Do not re-enter on the same bar after an exit.
        if p is None and symbol not in broker.positions:
            sig=ENGINES[engine].signal(symbol,bars[:i])
            if sig:
                opened=broker.enter(sig,Quote(b.open,b.open))
                if opened:
                    stop=opened['stop']; target=opened['target']; side=opened['direction']
                    # Assume stop first if the candle crosses both stop and target.
                    if side=='BUY':
                        if b.low<=stop:broker.exit(symbol,Quote(stop,stop),'entry_bar_stop')
                        elif target is not None and b.high>=target:broker.exit(symbol,Quote(target,target),'entry_bar_target')
                    else:
                        if b.high>=stop:broker.exit(symbol,Quote(stop,stop),'entry_bar_stop')
                        elif target is not None and b.low<=target:broker.exit(symbol,Quote(target,target),'entry_bar_target')
    if symbol in broker.positions:
        broker.exit(symbol,Quote(bars[-1].close,bars[-1].close),'end_of_data')
    wins=sum(t['pnl']>0 for t in broker.trades)
    return {'engine':engine,'symbol':symbol,'trades':len(broker.trades),'wins':wins,'win_rate':wins/len(broker.trades) if broker.trades else None,'net_pnl':round(sum(t['pnl'] for t in broker.trades),2),'ending_equity':round(risk.equity,2),'trades_log':broker.trades}
