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
from routes_opportunity import member
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
    limit:int=Field(default=5,ge=1,le=10)
    minimum_score:int=Field(default=70,ge=50,le=95)
    symbol:str|None=Field(default=None,pattern=r'^[A-Z][A-Z0-9.]{0,11}$')


def setup(asset,quote,ai,now):
    """Fixed, disclosed components. Missing news/model confirmation earns no points."""
    x=quote.get('feature_vector')
    try:
        if not x or len(x)!=7 or not all(math.isfinite(v) for v in x):return None
        stamp=utc(quote['source_time']);price=float(quote['price'])
        if not 0<=(now-stamp).total_seconds()<1200 or not math.isfinite(price) or not price>0:return None
        r1,r4,_,trend,position,volume,atr=x
        if atr<=0 or atr>.1 or abs(r4)/atr>3.5:return None
        direction='BUY' if trend>0 and r4>0 and r1>0 else 'SELL' if trend<0 and r4<0 and r1<0 else None
        if direction is None:return None
        if ai.get('model_state')=='active' and ai.get('direction') in ('BUY','SELL') and ai['direction']!=direction:return None
        sign=1 if direction=='BUY' else -1
        points={'trend':round(25*min(1,abs(trend)/atr/.75),2),'momentum':20,
                'range':15 if (position>1 if sign>0 else position<0) else 8 if (position>.6 if sign>0 else position<.4) else 0,
                'risk':10 if abs(r4)/atr<=2 else 5,'news':0,'ai_confirmation':0}
        denominator=90 if asset['asset_class']=='forex' else 100
        if asset['asset_class']!='forex':points['volume']=10 if volume>=1.2 else 5 if volume>=.8 else 0
        tone=ai.get('sentiment',{}).get('sources',{}).get('news',{})
        if tone.get('samples') and tone.get('score') is not None:
            points['news']=10 if sign*tone['score']>=.05 else -10 if sign*tone['score']<=-.05 else 0
        confirmed=ai.get('model_state')=='active' and ai.get('direction')==direction
        if confirmed:points['ai_confirmation']=10
        score=round(max(0,min(100,100*sum(points.values())/denominator)))
        stop=price-sign*atr*price*1.5;target=price+sign*atr*price*3
        if not math.isfinite(stop) or not math.isfinite(target) or stop<=0 or target<=0:return None
        return {'symbol':asset['symbol'],'asset_class':asset['asset_class'],'direction':direction,'score':score,
                'display_symbol':asset['symbol'][:3]+'/'+asset['symbol'][3:] if asset['asset_class']=='forex' else asset['symbol']+'/USD' if asset['asset_class']=='crypto' else asset['symbol'],
                'score_type':'Setup quality / 100; not a win probability','score_components':points,
                'basis':'KAOS technical setup + validated AI confirmation' if confirmed else 'KAOS technical setup; AI not confirming',
                'model_state':ai.get('model_state','unavailable'),'ai_confirmed':confirmed,
                'reference_entry':price,'reference_stop':stop,'reference_target':target,'reward_risk':2,
                'horizon':'45–60 minutes','reason':'Trend and short-term momentum agree; bounded volatility and risk levels.',
                'source':quote.get('source'),'source_time':quote['source_time'],
                'supporting_sources':ai.get('supporting_sources',[]),'expires_at':min(now+timedelta(minutes=5),stamp+timedelta(minutes=20)).isoformat(),
                'execution_enabled':False}
    except (ValueError,TypeError,KeyError):return None


async def evidence(assets):
    cutoff=(datetime.now(timezone.utc)-timedelta(days=7)).isoformat()
    rows=await db.kaos_intelligence.find({'asset':{'$in':[a['symbol'] for a in assets]},'published_at':{'$gte':cutoff}}, {'_id':0}).sort('published_at',-1).limit(200).to_list(200)
    # One shared cached news request, not one paid-provider call per candidate.
    import alpha_vantage
    from radar_news import normalize
    from radar_sources import SourceIssue
    try:
        news=normalize(await alpha_vantage.news())
        stamp=datetime.now(timezone.utc).isoformat()
        for asset in assets:
            for row in news:
                if not {asset['symbol'],'CRYPTO:'+asset['symbol']}.intersection(row['tickers']):continue
                rows.append({'asset':asset['symbol'],'asset_class':asset['asset_class'],'source':'news',
                    'published_at':row['published_at'],'observed_at':stamp,'summary':row['title']+' '+row['summary'],
                    'source_url':row['source_url']})
    except SourceIssue:pass
    return rows


async def collect(market,focus=None):
    now=datetime.now(timezone.utc)
    if market=='options':
        import radar_settings
        cfg=await radar_settings.settings('options_data')
        if not cfg.get('enabled',True) or not cfg.get('api_key') or not cfg.get('api_secret') or cfg.get('configuration_error'):
            return {'plays':[],'market':market,'scanned':0,'universe_size':len(UNIVERSES[market]),
                'coverage':['The owner must connect OPRA options market data in Admin → Radar Sources. Stock candles alone cannot produce verified options plays.'],
                'partial':False,'completed_at':now.isoformat(),'execution_enabled':False,
                'status_message':'Options need OPRA chain access. The owner can connect it in Admin → Radar Sources.',
                'universe_note':'No chain access: no option contracts were fabricated.','score_explanation':'Options scores rank the underlying setup; fresh bid/ask and contract filters are also required.'}
    trending=await radar_trending.snapshot() if market=='stocks' else {'state':'unavailable'}
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
    rows=await evidence(assets)
    gate=asyncio.Semaphore(3);evaluated=[]
    async def candidate(asset):
        async with gate:
            try:
                quote=await asyncio.wait_for(radar_signals.market(SimpleNamespace(**asset)),timeout=10)
                report=await native.assessment(asset,quote,rows,datetime.now(timezone.utc),trending)
                play=setup(asset,quote,report,datetime.now(timezone.utc))
                if play and market=='options' and play['score']<70:
                    return {'symbol':asset['symbol'],'reason':'Underlying setup did not reach the options score threshold.'}
                if play and market=='options':
                    contract,message=await asyncio.wait_for(radar_options.chain(asset['symbol'],play['direction'],play['reference_entry'],datetime.now(timezone.utc)),timeout=8)
                    if contract is None:return {'symbol':asset['symbol'],'reason':message}
                    play.update(option=contract,direction=contract['type'],asset_class='option',option_note=message,
                        basis='Underlying setup · '+play['basis'],
                        expires_at=(utc(contract['quote_time'])+timedelta(seconds=120)).isoformat())
                return {'symbol':asset['symbol'],'play':play,'reason':report.get('explanation') if not play else None}
            except (asyncio.TimeoutError,ValueError,TypeError):return {'symbol':asset['symbol'],'reason':'Data did not finish within the scan budget.'}
    tasks=[asyncio.create_task(candidate(a)) for a in assets]
    try:
        done,pending=await asyncio.wait(tasks,timeout=35)
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
            'execution_enabled':False,'score_explanation':'Quality points: trend 25, momentum 20, range 15, risk 10, volume 10, news 10, validated AI agreement 10. Forex omits volume and scales the remaining 90 points to 100. Missing confirmation earns no points.',
            'universe_note':'Bounded liquid-market watchlist, with ApeWisdom leaders for stocks; not every listed instrument.',
            'started_at':now.isoformat()}


@router.post('/signals/opportunities')
async def opportunities(request:OpportunityInput,user=Depends(member)):
    key=request.market+':'+(request.symbol or 'universe')
    now=datetime.now(timezone.utc);stamp=now.timestamp()
    cached=await db.kaos_opportunity_scans.find_one({'_id':key})
    ttl=60 if request.market=='options' else 300
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
                    {'_id':user['id']+':'+request.market,'until':{'$lt':stamp}},
                    {'$set':{'until':stamp+30}},upsert=True)
            except DuplicateKeyError:raise HTTPException(429,'Wait 30 seconds before requesting another new scan in this market.')
            try:report=await asyncio.wait_for(collect(request.market,request.symbol),timeout=50)
            except asyncio.TimeoutError:
                raise HTTPException(504,'The scan did not finish within its time budget. Retry shortly; no plays were fabricated.')
            await db.kaos_opportunity_scans.update_one({'_id':key},{'$set':{'checked':datetime.now(timezone.utc).timestamp(),'report':report}},upsert=True)
        finally:await db.kaos_opportunity_locks.update_one({'_id':key},{'$set':{'until':0}})
    fresh=[r for r in report['plays'] if r['score']>=request.minimum_score and utc(r['expires_at'])>datetime.now(timezone.utc)]
    return {**report,'plays':fresh[:request.limit],'state':'complete','minimum_score':request.minimum_score,
            'message':None if fresh else report.get('status_message','No setups meet the score and freshness requirements. No plays were fabricated.')}
