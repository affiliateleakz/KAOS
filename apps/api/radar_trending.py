"""Keyless third-party mention rankings; never fabricates sentiment or X data."""
import asyncio
from datetime import datetime,timezone
import re
from fastapi import Depends,HTTPException
from pymongo.errors import DuplicateKeyError
from db import db
from radar_sources import Sources,SourceIssue
from routes_radar import router
from routes_opportunity import member

URL='https://apewisdom.io/api/v1.0/filter/all-stocks/page/1'


def integer(value,minimum=0):
    if isinstance(value,bool) or not re.fullmatch(r'\d+',str(value)):raise ValueError('Invalid count')
    number=int(value)
    if number<minimum or number>10**12:raise ValueError('Invalid count')
    return number


def normalize(data):
    if not isinstance(data,dict) or not isinstance(data.get('results'),list):raise ValueError('Missing ranking data')
    rows={}
    for raw in data['results'][:100]:
        try:
            symbol=str(raw['ticker']).upper()
            if not re.fullmatch(r'[A-Z][A-Z0-9.]{0,11}',symbol):continue
            mentions=integer(raw['mentions']);rank=integer(raw['rank'],1)
            def optional(field,minimum=0):
                try:return integer(raw.get(field),minimum)
                except ValueError:return None
            previous=optional('mentions_24h_ago');previous_rank=optional('rank_24h_ago',1)
            rows.setdefault(symbol,{'symbol':symbol,'name':str(raw.get('name',symbol))[:180],
                'mentions':mentions,'rank':rank,'upvotes':optional('upvotes'),
                'previous_mentions':previous,'previous_rank':previous_rank,
                'mention_change':mentions-previous if previous is not None else None,
                'rank_change':previous_rank-rank if previous_rank is not None else None,
                'source_url':'https://apewisdom.io/'})
        except (KeyError,ValueError,TypeError):continue
    if data['results'] and not rows:raise ValueError('Unusable ranking data')
    return sorted(rows.values(),key=lambda r:r['rank'])


async def snapshot():
    now=datetime.now(timezone.utc);stamp=now.timestamp()
    cached=await db.kaos_trending_cache.find_one({'_id':'stocks'})
    if cached and stamp-cached.get('checked',0)<(300 if cached.get('error') else 1800):
        if not cached.get('error'):return {**cached['report'],'cached':True}
        return unavailable(cached,cached['error'],stamp)
    try:
        await db.kaos_trending_locks.update_one({'_id':'stocks','until':{'$lt':stamp}},{'$set':{'until':stamp+20}},upsert=True)
    except DuplicateKeyError:
        return unavailable(cached,'Trending stocks are refreshing. Try again shortly.',stamp)
    session=Sources({})
    try:
        rows=normalize(await asyncio.wait_for(session.request('GET',URL),timeout=10))
        report={'state':'complete','provider':'ApeWisdom','rankings':rows,'fetched_at':now.isoformat(),
                'provider_updated_at':None,'cached':False,'stale':False,
                'coverage':'Provider-reported mentions in selected Reddit stock communities; top 100 results. No X coverage or individual posts.',
                'execution_enabled':False}
        await db.kaos_trending_cache.update_one({'_id':'stocks'},{'$set':{'checked':stamp,'report':report},'$unset':{'error':''}},upsert=True)
        return report
    except (SourceIssue,ValueError,TypeError,asyncio.TimeoutError) as error:
        message='ApeWisdom is temporarily unavailable. Please try again later.' if isinstance(error,(SourceIssue,asyncio.TimeoutError)) else 'The mention provider returned unusable data.'
        await db.kaos_trending_cache.update_one({'_id':'stocks'},{'$set':{'checked':stamp,'error':message}},upsert=True)
        return unavailable(cached,message,stamp)
    finally:
        await session.close()
        await db.kaos_trending_locks.update_one({'_id':'stocks'},{'$set':{'until':0}})


def unavailable(cached,message,now):
    old=(cached or {}).get('report')
    if old:
        try:
            if 0<=now-datetime.fromisoformat(old['fetched_at']).timestamp()<86400:
                return {**old,'state':'unavailable','stale':True,'cached':True,'message':message+' Showing a saved snapshot.'}
        except (ValueError,KeyError,TypeError):pass
    return {'state':'unavailable','provider':'ApeWisdom','rankings':[],'stale':True,'cached':False,
            'message':message,'fetched_at':None,'execution_enabled':False}


@router.get('/trending/stocks')
async def trending_stocks(user=Depends(member)):
    return await snapshot()


@router.post('/social/mentions')
async def retired_social_scanner(user=Depends(member)):
    raise HTTPException(410,'The direct social scanner was removed. Use Trending Stocks; no Reddit or X key is needed.')
