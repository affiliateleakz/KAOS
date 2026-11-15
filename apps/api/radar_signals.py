"""Separate candle research from short-expiry broker telemetry. Never submits orders."""
import asyncio
import math
from datetime import datetime, timezone, timedelta
import httpx
from fastapi import Depends
from routes_radar import router, ScanInput
from routes_opportunity import member
from db import db
from pymongo.errors import DuplicateKeyError
from kaos_opportunity import utc


def assess(candles, now):
    # Rows: timestamp, low, high, open, close, volume. Only closed 15m bars.
    rows = sorted({float(r[0]): [float(x) for x in r[:6]] for r in candles
                   if len(r) >= 6 and all(math.isfinite(float(x)) for x in r[:6])
                   and float(r[0]) + 900 <= now}.values())
    rows = [r for r in rows if 0 < r[1] <= min(r[3], r[4]) <= max(r[3], r[4]) <= r[2]]
    if len(rows) < 60:
        return {'direction': 'WAIT', 'reason': 'At least 60 closed 15-minute candles are required.'}
    last = rows[-1]
    base = {'source_time': datetime.fromtimestamp(last[0]+900, timezone.utc).isoformat(),
            'horizon': '45 minutes', 'method': 'EMA trend + 15-minute breakout; technical rules, not trained AI',
            'price': last[4], 'execution_enabled': False}
    if now - (last[0]+900) > 1200:
        return {**base, 'direction': 'WAIT', 'reason': 'Market data is stale or the market is closed.'}
    if any(b[0]-a[0] != 900 for a,b in zip(rows[-20:], rows[-19:])):
        return {**base, 'direction': 'WAIT', 'reason': 'Recent candle gaps; waiting for a complete trading session.'}
    def ema(period):
        value = rows[0][4]
        for row in rows[1:]:
            value += 2/(period+1)*(row[4]-value)
        return value
    atr = sum(max(r[2]-r[1], abs(r[2]-p[4]), abs(r[1]-p[4]))
              for p,r in zip(rows[-15:-1], rows[-14:]))/14
    prior = rows[-21:-1]
    direction = ('BUY' if ema(9)>ema(21) and last[4]>max(r[2] for r in prior)
                 else 'SELL' if ema(9)<ema(21) and last[4]<min(r[1] for r in prior) else 'WAIT')
    avg_volume = sum(r[5] for r in rows[-21:-1])/20
    high, low = max(r[2] for r in prior), min(r[1] for r in prior)
    features = [last[4]/rows[-2][4]-1, last[4]/rows[-5][4]-1,
                last[4]/rows[-21][4]-1, (ema(9)-ema(21))/last[4],
                (last[4]-low)/max(high-low,1e-9),
                min(20,last[5]/avg_volume) if avg_volume>0 else 0, atr/last[4]]
    result = {**base, 'feature_vector':features,
              'closed_history':[[r[0]+900,r[4]] for r in rows[-150:]], 'direction': direction, 'reason': 'Trend and closed-candle breakout agree.' if direction != 'WAIT' else 'No confirmed trend breakout.'}
    if direction != 'WAIT' and atr > 0:
        sign = 1 if direction == 'BUY' else -1
        result.update(reference_stop=last[4]-sign*1.5*atr, reference_target=last[4]+sign*3*atr)
    return result


async def market(asset):
    key = asset.asset_class+':'+asset.symbol
    now = datetime.now(timezone.utc).timestamp()
    cached = await db.kaos_market_signals.find_one({'_id': key})
    if cached and now-cached.get('checked', 0)<300:
        return cached['report']
    try:
        await db.kaos_market_signal_locks.update_one(
            {'_id':key, 'until':{'$lt':now}}, {'$set':{'until':now+20}}, upsert=True)
    except DuplicateKeyError:
        return cached['report'] if cached else {'symbol':asset.symbol,'direction':'WAIT','reason':'A shared scan is already running. Refresh shortly.'}
    try:
        async with httpx.AsyncClient(timeout=8, follow_redirects=False) as client:
            if asset.asset_class == 'crypto':
                response = await client.get(f'https://api.exchange.coinbase.com/products/{asset.symbol}-USD/candles', params={'granularity':900})
                response.raise_for_status()
                candles = response.json()
                source = 'Coinbase spot USD'
            elif asset.asset_class in ('stock', 'etf'):
                response = await client.get(f'https://query1.finance.yahoo.com/v8/finance/chart/{asset.symbol}', params={'interval':'15m','range':'1mo'}, headers={'User-Agent':'KAOS Radar/1.0'})
                response.raise_for_status()
                data = response.json()['chart']['result'][0]
                quote = data['indicators']['quote'][0]
                candles = [[t]+[quote[k][i] for k in ('low','high','open','close','volume')] for i,t in enumerate(data['timestamp']) if all(quote[k][i] is not None for k in ('low','high','open','close','volume'))]
                source = 'Yahoo Finance; may be delayed'
            else:
                return {'symbol':asset.symbol,'direction':'WAIT','reason':'This market does not have a supported candle source yet.'}
        report = {**assess(candles, now), 'symbol':asset.symbol, 'asset_class':asset.asset_class, 'source':source}
    except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError):
        report = {'symbol':asset.symbol,'direction':'WAIT','reason':'Candle source unavailable; no signal generated.'}
    await db.kaos_market_signals.update_one({'_id':key},{'$set':{'checked':now,'report':report}},upsert=True)
    await db.kaos_market_signal_locks.update_one({'_id':key},{'$set':{'until':0}})
    return report


@router.post('/signals/market')
async def market_signals(req: ScanInput, user=Depends(member)):
    from routes_radar import scan
    report = await scan(req.model_copy(update={'include_ai':True}), user)
    assets = report['ai'].get('report',{}).get('assets',[])
    return {'signals':[{**row, 'reason':row['explanation'],
                        'source':'KAOS local evidence model', 'method':'Learned multi-source evidence model; no external AI service'} for row in assets],
            'execution_enabled':False, 'ai_status':report['ai'].get('report',{}).get('summary'),
            'coverage_gaps':report['ai'].get('report',{}).get('coverage_gaps',[]), 'source_status':report['source_status'], 'cached':report['cached'], 'completed_at':report['completed_at']}


@router.get('/signals/bot')
async def bot_signals(user=Depends(member)):
    rows = await db.signals.find({'userId':user['id'], 'state':'SIGNAL_GENERATED'}, {'_id':0}).sort('createdAt',-1).to_list(20)
    now = datetime.now(timezone.utc)
    signals = []
    for row in rows:
        try:
            stamp = utc(row.get('signalTimestamp') or row['createdAt'])
            age = (now-stamp).total_seconds()
            expiry = str(row.get('expiration',''))
            ttl = {'30s':30,'45s':45}.get(expiry,0)
            if age < 0 or age >= ttl or row.get('simulated') or row.get('direction') not in ('BUY','SELL'):
                continue
            signals.append({**{k:row.get(k) for k in ('id','asset','platform','direction','engine','expiration','signalTimestamp','createdAt')}, 'expiresAt':(stamp+timedelta(seconds=ttl)).isoformat()})
        except (ValueError, TypeError, KeyError):
            continue
    return {'signals':signals,'provenance':'Extension-reported signals; not independently verified. Exact broker symbols retained.',
            'execution_enabled':False, 'maximum_age_seconds':45}


@router.get('/sentiment/history')
async def sentiment_history(symbol: str, asset_class: str = 'stock', user=Depends(member)):
    from routes_radar import Asset
    from pydantic import ValidationError
    from fastapi import HTTPException
    try:
        asset = Asset(symbol=symbol,asset_class=asset_class)
    except ValidationError:
        raise HTTPException(422,'Invalid market symbol or asset class')
    cutoff=(datetime.now(timezone.utc)-timedelta(days=7)).isoformat()
    rows=await db.kaos_radar_sentiment.find({'symbol':asset.symbol,'asset_class':asset.asset_class,
        'observed_at':{'$gte':cutoff}}, {'_id':0}).sort('observed_at',-1).limit(100).to_list(100)
    return {'history':list(reversed(rows)),'sampled':True,'background_worker':False}
