"""Bounded multi-market setup discovery; quality scores are not win probabilities."""
import asyncio
import math
from datetime import datetime,timezone,timedelta
from types import SimpleNamespace
from typing import Literal
from fastapi import Depends,HTTPException
from pydantic import BaseModel,Field,ConfigDict
from pymongo.errors import DuplicateKeyError
from db import db
from routes_radar import router
from routes_opportunity import member,signal_member
from kaos_opportunity import utc
import radar_signals
import kaos_radar_ai as native
import radar_trending
import radar_options

UNIVERSES={
 'stocks':['AAPL','NVDA','MSFT','AMZN','META','TSLA','AMD','GOOGL','AVGO','NFLX','JPM','XOM','PLTR','COIN','SPY','QQQ'],
 'crypto':['BTC','ETH','SOL','XRP','ADA','DOGE','AVAX','LINK','LTC','BCH','DOT','UNI'],
 'forex':['EURUSD','GBPUSD','USDJPY','AUDUSD','USDCAD','USDCHF','NZDUSD','EURGBP'],
 'options':['SPY','QQQ','AAPL','NVDA','TSLA','AMD','MSFT','AMZN','META','GOOGL'],
}


class OpportunityInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    market:Literal['stocks','crypto','forex','options']='stocks'
    timeframe:Literal['any','intraday','daily','weekly','monthly']='daily'
    limit:int=Field(default=5,ge=1,le=10)
    minimum_score:int=Field(default=70,ge=50,le=95)
    symbol:str|None=Field(default=None,pattern=r'^[A-Z][A-Z0-9.]{0,11}$')


def setup(asset,quote,ai,now):
    """Convert the shared research score into an eligible, expiring setup."""
    from radar_scoring import score
    quote=ai.get('market_snapshot') or quote
    card=ai.get('scorecard') or score(asset,quote,ai,now)
    if not card['eligible'] or card['direction'] not in ('BUY','SELL'):return None
    try:
        price=float(quote['price']);atr=quote['feature_vector'][6]
        sign=1 if card['direction']=='BUY' else -1
        scale=math.sqrt({'daily':1,'weekly':5,'monthly':21}.get(quote.get('timeframe'),1))
        stop=price-sign*atr*price*1.5*scale;target=price+sign*atr*price*3*scale
        if not math.isfinite(stop) or not math.isfinite(target) or stop<=0 or target<=0:return None
        stamp=utc(quote['source_time'])
        return {'symbol':asset['symbol'],'asset_class':asset['asset_class'],'direction':card['direction'],'score':card['score'],
            'display_symbol':asset['symbol'][:3]+'/'+asset['symbol'][3:] if asset['asset_class']=='forex' else asset['symbol']+'/USD' if asset['asset_class']=='crypto' else asset['symbol'],
            'score_type':'Setup quality / 100; not a win probability','score_components':card['components'],
            'coverage_percent':card['coverage_percent'],'context_level':card.get('context_level','Limited evidence'),
            'score_coverage':card['coverage'],'score_version':card['version'],
            'basis':'KAOS evidence score + validated AI confirmation' if card.get('ai_confirmed') else 'KAOS evidence score; AI not confirming',
            'model_state':ai.get('model_state','unavailable'),'ai_confirmed':card.get('ai_confirmed',False),
            'reference_entry':price,'reference_stop':stop,'reference_target':target,'reward_risk':2,
            'timeframe':quote.get('timeframe','intraday'),'planning':quote.get('planning',False),
            'plan_note':'Last completed daily session; revalidate price, news and liquidity before entry. Weekly/monthly levels scale daily ATR by the square root of 5/21 sessions; these are planning estimates.' if quote.get('planning') else None,
            'horizon':quote.get('horizon','45–60 minutes'),'reason':card['reason'],'attention':ai.get('attention'),
            'source':quote.get('source'),'source_time':quote['source_time'],
            'supporting_sources':ai.get('supporting_sources',[]),
            'expires_at':(now+timedelta(minutes=15) if quote.get('planning') else min(now+timedelta(minutes=5),stamp+timedelta(minutes=20))).isoformat(),'execution_enabled':False}
    except (ValueError,TypeError,KeyError):return None


async def collect(market,focus=None,timeframe='intraday',shared=None):
    now=datetime.now(timezone.utc)
    if market=='options' and timeframe=='intraday':
        import radar_settings
        cfg=await radar_settings.settings('options_data')
        if not cfg.get('enabled',True) or not cfg.get('api_key') or not cfg.get('api_secret') or cfg.get('configuration_error'):
            return {'plays':[],'market':market,'scanned':0,'universe_size':len(UNIVERSES[market]),
                'coverage':['The owner must connect OPRA options market data in Admin → Radar Sources. Stock candles alone cannot produce verified options plays.'],
                'partial':False,'completed_at':now.isoformat(),'execution_enabled':False,
                'status_message':'Options need OPRA chain access. The owner can connect it in Admin → Radar Sources.',
                'universe_note':'No chain access: no option contracts were fabricated.','score_explanation':'Options scores rank the underlying setup; fresh bid/ask and contract filters are also required.'}
    if shared is not None and market=='stocks':
        if 'trending' not in shared:shared['trending']=asyncio.create_task(radar_trending.snapshot())
        trending=await shared['trending']
    else:trending=await radar_trending.snapshot() if market=='stocks' else {'state':'unavailable'}
    symbols=UNIVERSES[market]
    if market=='stocks' and trending.get('state')=='complete' and not trending.get('stale'):
        symbols=list(dict.fromkeys([r['symbol'] for r in trending.get('rankings',[])[:6]]+symbols))[:16]
    if focus:
        allowed=set(UNIVERSES[market])
        if market=='stocks':allowed.update(r['symbol'] for r in trending.get('rankings',[]))
        if focus not in allowed:raise HTTPException(422,'This instrument is outside the current scan universe.')
        symbols=[focus]
    kind={'stocks':'stock','crypto':'crypto','forex':'forex','options':'stock'}[market]
    assets=[{'symbol':s,'asset_class':kind} for s in symbols]
    await native.ensure_indexes()
    import radar_research
    if shared is not None:
        if 'context' not in shared:shared['context']=asyncio.create_task(radar_research.context(assets,budget=12))
        context_data=await shared['context']
    else:context_data=await radar_research.context(assets,budget=12)
    gate=asyncio.Semaphore(3);evaluated=[]
    async def candidate(asset):
        async with gate:
            try:
                quote=await asyncio.wait_for((radar_signals.market(SimpleNamespace(**asset)) if timeframe=='intraday' else radar_signals.market(SimpleNamespace(**asset),timeframe)),timeout=10)
                report=await radar_research.asset_report(asset,context_data,trending,quote)
                play=setup(asset,quote,report,datetime.now(timezone.utc))
                if play and market=='options' and play['score']<70:
                    return {'symbol':asset['symbol'],'reason':'Underlying setup did not reach the options score threshold.'}
                if play and market=='options' and timeframe!='intraday':
                    play.update(direction='CALL' if play['direction']=='BUY' else 'PUT',asset_class='option',
                        option_note='Underlying directional options research only. No contract or premium selected. Verify a live chain, expiry beyond the outlook, spread, liquidity and Greeks before entry.')
                if play and market=='options' and timeframe=='intraday':
                    contract,message=await asyncio.wait_for(radar_options.chain(asset['symbol'],play['direction'],play['reference_entry'],datetime.now(timezone.utc)),timeout=8)
                    if contract is None:return {'symbol':asset['symbol'],'reason':message}
                    play.update(option=contract,direction=contract['type'],asset_class='option',option_note=message,
                        basis='Underlying setup · '+play['basis'],
                        expires_at=(utc(contract['quote_time'])+timedelta(seconds=120)).isoformat())
                return {'symbol':asset['symbol'],'play':play,'reason':report.get('explanation') if not play else None}
            except (asyncio.TimeoutError,ValueError,TypeError):return {'symbol':asset['symbol'],'reason':'Data did not finish within the scan budget.'}
    tasks=[asyncio.create_task(candidate(a)) for a in assets]
    try:
        done,pending=await asyncio.wait(tasks,timeout=25)
        for task in tasks:
            if task in done:
                try:evaluated.append(task.result())
                except Exception:evaluated.append({'symbol':assets[tasks.index(task)]['symbol'],'reason':'Candidate data could not be validated.'})
        for task in pending:task.cancel()
        if pending:await asyncio.gather(*pending,return_exceptions=True)
    finally:
        for task in tasks:
            if not task.done():task.cancel()
        await asyncio.gather(*tasks,return_exceptions=True)
    plays=sorted([r['play'] for r in evaluated if r.get('play')],key=lambda r:(-r['score'],r['symbol']))
    return {'plays':plays,'market':market,'scanned':len(evaluated),'universe_size':len(assets),
            'coverage':sorted({r['reason'] for r in evaluated if r.get('reason')}),
            'partial':len(evaluated)<len(assets),'completed_at':datetime.now(timezone.utc).isoformat(),
            'execution_enabled':False,'score_explanation':'Shared research score: market setup up to 80, news/text 5, attention 3, disclosures 3, large-holder activity 3, derivatives/macro/liquidity 2, validated AI 4. Missing evidence earns no points and is shown in coverage. Forex omits volume and scales 90 points to 100.',
            'universe_note':'Bounded liquid-market watchlist, with ApeWisdom leaders for stocks; not every listed instrument.',
            'started_at':now.isoformat()}


async def collect_any(market,focus=None):
    """Warm shared daily candles, then assess each horizon with its own model."""
    shared={}
    intraday,daily=await asyncio.gather(collect(market,focus,'intraday',shared),collect(market,focus,'daily',shared))
    weekly,monthly=await asyncio.gather(collect(market,focus,'weekly',shared),collect(market,focus,'monthly',shared))
    reports=[intraday,daily,weekly,monthly]
    return {**daily,'plays':sorted([p for r in reports for p in r['plays']],key=lambda p:(-p['score'],p['symbol'],p['timeframe'])),
        'timeframe':'any','scanned':sum(r['scanned'] for r in reports),'universe_size':sum(r['universe_size'] for r in reports),
        'partial':any(r.get('partial',False) for r in reports),
        'coverage':sorted({text for r in reports for text in r.get('coverage',[])}),'status_message':None,
        'universe_note':daily.get('universe_note','')+' Each market/timeframe has its own trained model. Daily bars and provider evidence are shared; outcomes and model decisions are separate.'}


@router.post('/signals/opportunities')
async def opportunities(request:OpportunityInput,user=Depends(signal_member)):
    key=request.market+':'+(request.symbol or 'universe')+':'+request.timeframe
    now=datetime.now(timezone.utc);stamp=now.timestamp()
    cached=await db.kaos_opportunity_scans.find_one({'_id':key})
    ttl=60 if request.market=='options' and request.timeframe=='intraday' else 300
    report=None
    if cached and 0<=stamp-cached.get('checked',0)<ttl:report=cached.get('report')
    if report is None:
        try:
            await db.kaos_opportunity_locks.update_one({'_id':key,'until':{'$lt':stamp}},{'$set':{'until':stamp+60}},upsert=True)
        except DuplicateKeyError:
            return {'plays':[],'state':'collecting','market':request.market,'message':'A shared scan is running. Results will refresh shortly.','execution_enabled':False}
        try:
            try:
                await db.kaos_opportunity_member_limits.update_one(
                    {'_id':user['id']+':'+request.market+':'+request.timeframe,'until':{'$lt':stamp}},
                    {'$set':{'until':stamp+30}},upsert=True)
            except DuplicateKeyError:raise HTTPException(429,'Wait 30 seconds before requesting another new scan in this market and timeframe.')
            try:report=await asyncio.wait_for((collect_any(request.market,request.symbol) if request.timeframe=='any' else collect(request.market,request.symbol,request.timeframe)),timeout=50)
            except asyncio.TimeoutError:
                raise HTTPException(504,'The scan did not finish within its time budget. Retry shortly; no plays were fabricated.')
            await db.kaos_opportunity_scans.update_one({'_id':key},{'$set':{'checked':datetime.now(timezone.utc).timestamp(),'report':report}},upsert=True)
        finally:await db.kaos_opportunity_locks.update_one({'_id':key},{'$set':{'until':0}})
    fresh=[r for r in report['plays'] if r['score']>=request.minimum_score and utc(r['expires_at'])>datetime.now(timezone.utc)]
    return {**report,'timeframe':request.timeframe,'plays':fresh[:request.limit],'state':'complete','minimum_score':request.minimum_score,
            'message':None if fresh else (report.get('status_message') or 'No setups meet the score and freshness requirements. No plays were fabricated.')}
