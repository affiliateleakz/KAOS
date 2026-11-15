"""Stock discovery from bounded Reddit/X feeds, not platform-wide mention counts."""
import asyncio
import csv
import io
import json
import re
from datetime import datetime, timezone, timedelta
from hashlib import sha256
from fastapi import Depends, HTTPException
from pymongo.errors import DuplicateKeyError
from db import db
from radar_sources import Sources, SourceIssue, timestamp
from radar_sentiment import text_score
from routes_radar import router
from routes_opportunity import member
import radar_settings

# Bare ticker words are particularly ambiguous; explicit cashtags remain eligible.
AMBIGUOUS=set('A I IT ON ALL ARE FOR SO OR AN AS AT BE BY DO GO HE IF IN IS ME MY NO OF OK ONE OUT TO UP US WE YOU CEO CFO GDP IPO USA AI DD AND THE NEW NOW WHY HOW CAN HAS HAD NOT BIG LOW HIGH JUST GOOD VERY WELL MORE THIS THAT WITH FROM'.split())
FEED='stocks+wallstreetbets+investing'


def extract(text, symbols):
    tagged={m.upper() for m in re.findall(r'\$([A-Za-z][A-Za-z0-9]*(?:\.[A-Za-z])?)\b',text)}
    bare=set(re.findall(r'(?<![A-Za-z0-9$])([A-Z][A-Z0-9]*(?:\.[A-Z])?)(?![A-Za-z0-9])',text))-AMBIGUOUS
    return (tagged|bare)&symbols.keys()


async def directory(session):
    now=datetime.now(timezone.utc).timestamp()
    cached=await db.kaos_social_directory.find_one({'_id':'us-listed'})
    if cached and now-cached.get('checked',0)<86400:return cached['symbols'],cached['scope']
    async def listing(name):
        raw=await session.request('GET','https://www.nasdaqtrader.com/dynamic/SymDir/'+name,raw=True)
        return list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig')),delimiter='|'))
    try:
        listings=await asyncio.gather(listing('nasdaqlisted.txt'),listing('otherlisted.txt'),return_exceptions=True)
        if any(isinstance(value,Exception) for value in listings):raise SourceIssue('unavailable','Stock directory unavailable')
        nasdaq,other=listings
        symbols={}
        for row in nasdaq+other:
            symbol=row.get('Symbol') or row.get('ACT Symbol')
            if row.get('Test Issue')=='Y' or not re.fullmatch(r'[A-Z][A-Z0-9]{0,5}(?:\.[A-Z])?',symbol or ''):continue
            symbols[symbol]={'name':row.get('Security Name',symbol)[:180],'asset_class':'etf' if row.get('ETF')=='Y' else 'stock'}
        if len(symbols)<100:raise ValueError('Incomplete directory')
        scope='NASDAQ Trader US-listed stock/ETF symbol directory; not OTC or worldwide listings'
    except (SourceIssue,ValueError,UnicodeError):
        if cached:return cached['symbols'],'Stale symbol directory; recently listed stocks may be missing'
        from routes_stock_heatmap import WATCHLIST
        symbols={s:{'name':s,'asset_class':'etf' if group=='ETFs' else 'stock'} for group,rows in WATCHLIST.items() for s in rows}
        symbols.update({s:{'name':s,'asset_class':'stock'} for s in ('GME','AMC','PLTR','SOFI','HOOD','RIVN','MSTR')})
        return symbols,'Fallback KAOS stock/ETF list only; directory unavailable, other tickers are excluded'
    await db.kaos_social_directory.update_one({'_id':'us-listed'},{'$set':{'checked':now,'symbols':symbols,'scope':scope}},upsert=True)
    return symbols,scope


async def feed(session, provider):
    try:
        if provider=='reddit':
            cfg=session.config('reddit',('client_id','client_secret','user_agent'))
            token=await session.reddit_token(cfg)
            data=await session.request('GET',f'https://oauth.reddit.com/r/{FEED}/new',
                headers={'Authorization':'Bearer '+token,'User-Agent':cfg['user_agent']},params={'limit':100,'raw_json':1})
            children=data.get('data',{}).get('children')
            if not isinstance(children,list):raise SourceIssue('unavailable','Invalid Reddit listing response')
            posts=[]
            for child in children[:100]:
                row=child.get('data') or {};identity=str(row.get('id',''))
                if not re.fullmatch(r'[A-Za-z0-9]+',identity):continue
                posts.append({'id':identity,'author':str(row.get('author','')),'text':(str(row.get('title',''))+' '+str(row.get('selftext','')))[:1200],
                              'published_at':row.get('created_utc'),'url':'https://www.reddit.com/comments/'+identity})
            scope='Latest 100 posts from r/stocks + r/wallstreetbets + r/investing, no comments'
        else:
            cfg=session.config('x',('bearer_token',))
            data=await session.request('GET','https://api.x.com/2/tweets/search/recent',
                headers={'Authorization':'Bearer '+cfg['bearer_token']},params={
                    'query':'(stock OR stocks OR shares OR earnings OR #stocks) lang:en -is:retweet',
                    'max_results':100,'start_time':(datetime.now(timezone.utc)-timedelta(hours=24)).strftime('%Y-%m-%dT%H:%M:%SZ'),
                    'tweet.fields':'created_at,author_id'})
            if data.get('errors') and 'data' not in data:raise SourceIssue('access_denied','X recent search requires permitted API access')
            items=data.get('data',[])
            if not isinstance(items,list):raise SourceIssue('unavailable','Invalid X listing response')
            posts=[{'id':str(row['id']),'author':str(row.get('author_id','')),'text':str(row.get('text',''))[:1200],
                    'published_at':row.get('created_at'),'url':'https://x.com/i/web/status/'+str(row['id'])}
                   for row in items[:100] if re.fullmatch(r'\d+',str(row.get('id','')))]
            scope='Latest 100 English financial-term search results, reposts excluded; not all cashtags or all X'
        return {'provider':provider,'state':'collected','scope':scope,'posts':posts,'inspected':len(posts)}
    except SourceIssue as error:
        return {'provider':provider,'state':error.state,'message':error.message,'posts':[],'inspected':None}
    except (ValueError,TypeError,KeyError,AttributeError):
        return {'provider':provider,'state':'unavailable','message':'Invalid source data','posts':[],'inspected':None}


def rank(feeds,symbols,now):
    ranked={};seen=set();observed=[]
    for source in feeds:
        for post in source['posts']:
            identity=(source['provider'],post['id'])
            if identity in seen:continue
            seen.add(identity)
            try:published=timestamp(post['published_at'])
            except (ValueError,TypeError,OverflowError,OSError):continue
            if not now-timedelta(hours=24)<=published<=now:continue
            found=extract(post['text'],symbols)
            if not found:continue
            observed.append(published)
            score=text_score(post['text'])
            for symbol in found:
                row=ranked.setdefault(symbol,{'symbol':symbol,**symbols[symbol],'mentions':0,'reddit':0,'x':0,'authors':set(),'scores':[],'posts':[]})
                row['mentions']+=1;row[source['provider']]+=1;row['scores'].append(score)
                if post['author'] and post['author']!='[deleted]':row['authors'].add((source['provider'],post['author']))
                if sum(p['provider']==source['provider'] for p in row['posts'])<4:row['posts'].append({'provider':source['provider'],'text':post['text'],
                    'source_url':post['url'],'published_at':published.isoformat(),'sentiment':score})
    rows=[]
    for row in ranked.values():
        scores=row.pop('scores');row['unique_authors']=len(row.pop('authors'))
        row.update(sentiment=sum(scores)/len(scores),bullish=sum(s>=.05 for s in scores),bearish=sum(s<=-.05 for s in scores),neutral=sum(-.05<s<.05 for s in scores))
        rows.append(row)
    return sorted(rows,key=lambda r:(-r['mentions'],r['symbol']))[:50], min(observed).isoformat() if observed else None


@router.post('/social/mentions')
async def social_mentions(user=Depends(member)):
    settings=dict(zip(('reddit','x'),await asyncio.gather(*(radar_settings.settings(p) for p in ('reddit','x')))))
    key=sha256(json.dumps(settings,sort_keys=True).encode()).hexdigest()
    now=datetime.now(timezone.utc);stamp=now.timestamp()
    cached=await db.kaos_social_mentions.find_one({'_id':key})
    if cached and stamp-cached.get('checked',0)<300:return {**cached['report'],'cached':True}
    try:
        await db.kaos_social_mentions_locks.update_one({'_id':key,'until':{'$lt':stamp}},{'$set':{'until':stamp+45}},upsert=True)
    except DuplicateKeyError:
        if cached:return {**cached['report'],'cached':True}
        raise HTTPException(409,'The shared social scan is running; refresh shortly')
    session=Sources(settings)
    try:
        async def collect():
            feeds=await asyncio.gather(feed(session,'reddit'),feed(session,'x'))
            symbols,scope=await directory(session) if any(row['posts'] for row in feeds) else ({},'No posts returned; ticker directory was not requested')
            return symbols,scope,feeds
        symbols,scope,feeds=await asyncio.wait_for(collect(),timeout=25)
        rows,oldest=rank(feeds,symbols,datetime.now(timezone.utc))
        for source in feeds:source.pop('posts',None)
        report={'rankings':rows,'source_status':feeds,'directory_scope':scope,'oldest_counted_post':oldest,
                'completed_at':datetime.now(timezone.utc).isoformat(),'cached':False,
                'counting':'Distinct source posts per ticker in bounded last-24-hour samples; repeats in one post count once. Authors are not verified people; counts are not platform-wide totals.',
                'sentiment_method':'Local English VADER, not a trade signal','execution_enabled':False}
        await db.kaos_social_mentions.update_one({'_id':key},{'$set':{'checked':stamp,'report':report}},upsert=True)
        return report
    except asyncio.TimeoutError:
        report={'rankings':[],'source_status':[{'provider':p,'state':'time_budget','inspected':None,
            'message':'The bounded scan timed out; no mention count is available'} for p in ('reddit','x')],
            'directory_scope':'Discovery did not complete','completed_at':datetime.now(timezone.utc).isoformat(),
            'oldest_counted_post':None,'counting':'No mention counts were fabricated. Retry after the five-minute cache expires.',
            'sentiment_method':'Local English VADER','execution_enabled':False,'cached':False}
        await db.kaos_social_mentions.update_one({'_id':key},{'$set':{'checked':stamp,'report':report}},upsert=True)
        return report
    except ImportError:
        raise HTTPException(503,'Install updated backend requirements for local sentiment monitoring')
    finally:
        await session.close()
        await db.kaos_social_mentions_locks.update_one({'_id':key},{'$set':{'until':0}})
