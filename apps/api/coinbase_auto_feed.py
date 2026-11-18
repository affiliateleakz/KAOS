"""Genuine Coinbase Exchange trades -> closed 5s candles. Never fabricate gaps."""
from datetime import datetime
from decimal import Decimal


class TradeFeed:
    def __init__(self):
        self.last_id=None;self.buckets={};self.rows=[];self.start_at=None

    def update(self,trades,now_ms):
        if not isinstance(trades,list) or not trades:raise ValueError('Coinbase trades unavailable')
        normalized=[]
        for trade in trades:
            stamp=int(datetime.fromisoformat(trade['time'].replace('Z','+00:00')).timestamp()*1000)
            price=Decimal(str(trade['price']));identifier=int(trade['trade_id'])
            if not price.is_finite() or price<=0 or stamp>now_ms+2000:raise ValueError('Invalid Coinbase trade')
            normalized.append((identifier,stamp,float(price)))
        normalized.sort()
        if len({r[0] for r in normalized})!=len(normalized):raise ValueError('Duplicate Coinbase trade identities')
        if now_ms-normalized[-1][1]>15000:raise ValueError('Coinbase feed is stale')
        if self.last_id is None:
            self.last_id=normalized[-1][0];self.start_at=(normalized[-1][1]//5000+1)*5000;return []  # Start a complete interval; don't invent historical coverage.
        fresh=[r for r in normalized if r[0]>self.last_id]
        if fresh and (fresh[0][0]!=self.last_id+1 or any(b[0]!=a[0]+1 for a,b in zip(fresh,fresh[1:]))):
            self.rows=[];self.buckets={};self.last_id=normalized[-1][0];self.start_at=(normalized[-1][1]//5000+1)*5000
            raise ValueError('Coinbase trade gap: closed-candle warmup restarted')
        for identifier,stamp,price in fresh:
            bucket=stamp//5000*5000
            if bucket<self.start_at:
                self.last_id=identifier;continue
            if self.rows and bucket<=self.rows[-1]['ts']:raise ValueError('Late Coinbase trade: refuse revised signal history')
            row=self.buckets.get(bucket)
            if row:
                row.update(high=max(row['high'],price),low=min(row['low'],price),close=price)
            else:self.buckets[bucket]={'ts':bucket,'closeTs':bucket+4999,'open':price,'high':price,'low':price,'close':price}
            self.last_id=identifier
        # Finalize only after later trades prove the prior bucket's sequence is complete.
        latest=max((stamp//5000*5000 for _,stamp,_ in normalized),default=0)
        for key in sorted(k for k in self.buckets if k<latest):
            if self.rows and key!=self.rows[-1]['ts']+5000:self.rows=[]
            self.rows.append(self.buckets.pop(key))
        self.rows=self.rows[-600:]
        return self.rows
