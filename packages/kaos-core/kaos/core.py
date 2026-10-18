"""KAOS research/paper execution core. Never places live broker orders."""
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional
import math

@dataclass(frozen=True)
class Bar:
    ts: str
    open: float
    high: float
    low: float
    close: float
    volume: float = 0
    def __post_init__(self):
        if not (math.isfinite(self.open) and math.isfinite(self.high) and math.isfinite(self.low) and math.isfinite(self.close) and math.isfinite(self.volume)):
            raise ValueError('nonfinite bar')
        if self.low <= 0 or self.low > min(self.open,self.close) or self.high < max(self.open,self.close) or self.high < self.low or self.volume < 0:
            raise ValueError('invalid OHLCV')

@dataclass(frozen=True)
class Signal:
    engine: str
    symbol: str
    direction: str
    reason: str
    score: int
    stop: Optional[float] = None
    target: Optional[float] = None

@dataclass(frozen=True)
class Quote:
    bid: float
    ask: float
    def __post_init__(self):
        if self.bid <= 0 or self.ask < self.bid:
            raise ValueError('invalid quote')

class RiskGuard:
    def __init__(self, initial_equity=10000.0, risk_fraction=0.005, daily_loss_limit=0.02, max_notional_fraction=0.10):
        self.equity=float(initial_equity)
        self.start_equity=float(initial_equity)
        self.risk_fraction=float(risk_fraction)
        self.daily_loss_limit=float(daily_loss_limit)
        self.max_notional_fraction=float(max_notional_fraction)
        self.realized_day=0.
        self.kill_switch=False
        if self.equity <= 0 or not 0 < risk_fraction <= .02 or not 0 < daily_loss_limit <= .20 or not 0 < max_notional_fraction <= 1:
            raise ValueError('unsafe risk config')
    def qty(self, side, entry, stop):
        if self.kill_switch or self.realized_day <= -self.start_equity*self.daily_loss_limit or side not in ('BUY','SELL'):
            return 0.
        if entry <= 0 or stop is None or (side=='BUY' and stop>=entry) or (side=='SELL' and stop<=entry):
            return 0.
        d=abs(entry-stop)
        return max(0., min(self.equity*self.risk_fraction/d, self.equity*self.max_notional_fraction/entry))
    def settle(self, pnl):
        self.realized_day+=pnl
        self.equity+=pnl
        if self.equity<=0 or self.realized_day <= -self.start_equity*self.daily_loss_limit:
            self.kill_switch=True
    def next_session(self):
        self.start_equity=self.equity;self.realized_day=0

class PaperBroker:
    """Simplified fill simulator; does not model queues or partial fills."""
    def __init__(self, guard: RiskGuard, fee_bps=10, slippage_bps=2):
        self.guard=guard
        self.fee_bps=float(fee_bps)
        self.slippage_bps=float(slippage_bps)
        self.positions={}
        self.trades=[]
        if min(self.fee_bps,self.slippage_bps)<0: raise ValueError('negative costs')
    def enter(self, sig: Signal, quote: Quote):
        if sig.symbol in self.positions or sig.direction not in ('BUY','SELL'): return None
        px=(quote.ask if sig.direction=='BUY' else quote.bid)*(1+(self.slippage_bps/10000 if sig.direction=='BUY' else -self.slippage_bps/10000))
        qty=self.guard.qty(sig.direction,px,sig.stop)
        if qty <= 0: return None
        fee=qty*px*self.fee_bps/10000
        rec={'engine':sig.engine,'symbol':sig.symbol,'direction':sig.direction,'qty':qty,'entry':px,'stop':sig.stop,'target':sig.target,'open_fee':fee,'reason':sig.reason}
        self.positions[sig.symbol]=rec
        return rec
    def exit(self, symbol, quote: Quote, reason='manual'):
        p=self.positions.pop(symbol,None)
        if p is None: return None
        side=p['direction']
        px=(quote.bid if side=='BUY' else quote.ask)*(1+(-self.slippage_bps/10000 if side=='BUY' else self.slippage_bps/10000))
        fee=p['qty']*px*self.fee_bps/10000
        pnl=p['qty']*(px-p['entry'])*(1 if side=='BUY' else -1)-p['open_fee']-fee
        out={**p,'exit':px,'close_fee':fee,'pnl':pnl,'exit_reason':reason}
        self.trades.append(out);self.guard.settle(pnl)
        return out

class BaseEngine:
    name='base'
    def signal(self,symbol,bars,**kwargs): raise NotImplementedError
    @staticmethod
    def atr(bars,n=14):
        if len(bars)<n+1:return None
        tr=[max(b.high-b.low,abs(b.high-prev.close),abs(b.low-prev.close)) for prev,b in zip(bars[:-1],bars[1:])]
        return sum(tr[-n:])/n

class CryptoEngine(BaseEngine):
    name='crypto'
    def signal(self,symbol,bars,**kw):
        # Research-only trend breakout with minimum range and conservative long spot direction.
        if len(bars)<35:return None
        a=self.atr(bars)
        if a is None or a<=0:return None
        last=bars[-1]; prior=bars[-21:-1]
        ma_fast=sum(b.close for b in bars[-10:])/10
        ma_slow=sum(b.close for b in bars[-30:])/30
        resistance=max(b.high for b in prior)
        if ma_fast>ma_slow and last.close>resistance and last.close-last.open>=.3*a:
            stop=last.close-2*a
            return Signal(self.name,symbol,'BUY','trend + 20-bar breakout',70,stop,last.close+3*a)
        return None

class StockEngine(BaseEngine):
    name='stock'
    def signal(self,symbol,bars,**kw):
        if len(bars)<31:return None
        a=self.atr(bars)
        if not a or a<=0:return None
        last=bars[-1]; prev=bars[-21:-1]
        vols=[b.volume for b in prev]
        if not vols or sum(vols)<=0:return None
        vavg=sum(vols)/len(vols)
        if last.close>max(b.high for b in prev) and last.volume>=1.5*vavg and last.close>sum(b.close for b in bars[-30:])/30:
            return Signal(self.name,symbol,'BUY','relative volume + 20-bar breakout',75,last.close-2*a,last.close+3*a)
        return None

class ForexEngine(BaseEngine):
    name='forex'
    def signal(self,symbol,bars,**kw):
        if len(bars)<31:return None
        a=self.atr(bars)
        if not a or a<=0:return None
        last=bars[-1]; prior=bars[-21:-1]
        hi=max(b.high for b in prior);lo=min(b.low for b in prior)
        if last.close>hi:return Signal(self.name,symbol,'BUY','20-bar range break',60,last.close-1.5*a,last.close+2.5*a)
        if last.close<lo:return Signal(self.name,symbol,'SELL','20-bar range break',60,last.close+1.5*a,last.close-2.5*a)
        return None

class OptionsEngine(BaseEngine):
    name='options'
    def signal(self,symbol,bars,**kw):
        # Fail closed: options require contract bid/ask, multiplier, Greeks & expiry; no underlying-only orders.
        return None

class PocketOptionEngine(BaseEngine):
    name='pocketoption'
    def signal(self,symbol,bars,**kw):
        # Requires a separate broker settlement model, payout and quote source.
        return None

ENGINES={e.name:e() for e in (CryptoEngine,StockEngine,ForexEngine,OptionsEngine,PocketOptionEngine)}
