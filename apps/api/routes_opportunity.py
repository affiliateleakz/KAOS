"""Research-only KAOS Opportunity Radar API. Collector requires server-side token."""
import asyncio
import os
import time
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field, ValidationError
from typing import Literal
from auth import get_current_user
from db import db
from services_trading import get_entitlements
from kaos_opportunity import evaluate, SUPPORTED, SOURCES, utc
from kaos_source_health import summarize_health

router=APIRouter(prefix='/api/v1/intelligence',tags=['opportunity-radar'])

class SocialSampleMetrics(BaseModel):
    """A bounded public social sample, NOT a complete platform mention count."""
    provider: Literal['bluesky_search', 'bluesky_monitored_accounts']
    sampled_posts: int = Field(ge=0, le=3000)
    sampled_unique_authors: int = Field(ge=0, le=3000)
    previous_hour_posts: int | None = Field(default=None, ge=0, le=100)
    previous_hour_unique_authors: int | None = Field(default=None, ge=0, le=100)
    search_results_inspected: int | None = Field(default=None, ge=0, le=100)
    search_limit: int = Field(default=100, ge=1, le=100)
    coverage: Literal[
        'bounded_search_sample_not_platform_total',
        'bounded_monitored_accounts_not_platform_total',
    ]

class Observation(BaseModel):
    asset: str = Field(min_length=1,max_length=60)
    asset_class: Literal['stock','etf','option','crypto','dex','forex','future']
    source: Literal['technical','news','filing','social','insider','institutional','politician','onchain','options_flow','liquidity','macro','dark_pool','short_interest']
    direction: Literal['bullish','bearish','neutral']
    strength: float = Field(ge=0,le=1)
    event_id: str = Field(min_length=1,max_length=150)
    observed_at: datetime
    published_at: datetime
    source_url: str = Field(min_length=8,max_length=2000)
    summary: str = Field(default='',max_length=1200)
    sample_metrics: SocialSampleMetrics | None = None

async def member(user=Depends(get_current_user)):
    if not (await get_entitlements(user)).get('scanners'):
        raise HTTPException(403,'Scanners require a Pro or Ultimate membership')
    return user

@router.post('/ingest')
async def ingest(items: list[Observation], x_kaos_collector_key: str | None=Header(default=None)):
    from secrets import compare_digest
    key=os.getenv('KAOS_COLLECTOR_KEY','')
    if not key or not x_kaos_collector_key or not compare_digest(key,x_kaos_collector_key):
        raise HTTPException(403,'Collector authentication required')
    if len(items)>250: raise HTTPException(413,'Batch too large')
    count=0
    for item in items:
        record=item.model_dump(mode='json')
        observed=utc(record['observed_at']); published=utc(record['published_at'])
        if observed>datetime.now(timezone.utc) or published>observed:
            raise HTTPException(422,'Invalid event timing')
        record['asset']=record['asset'].upper()
        await db.kaos_intelligence.update_one({'source':record['source'],'event_id':record['event_id']},
                                                {'$set':record},upsert=True)
        count+=1
    return {'accepted':count,'mode':'research_only'}


_COLLECTORS_DIR=os.getenv('KAOS_COLLECTORS_DIR') or os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'services','collectors')
_NEWS_SYNC_SEEN={}
# After a GDELT failure, skip it briefly instead of making every member wait for the
# same timeout before the fallback feed is tried.
_GDELT_DOWN_UNTIL=0.0


def _gdelt_module():
    import importlib,sys
    if _COLLECTORS_DIR not in sys.path: sys.path.insert(0,_COLLECTORS_DIR)
    return importlib.import_module('gdelt_news')


@router.post('/sync-news')
async def sync_news(symbol: str=Query(min_length=1,max_length=12),
                    query: str | None=Query(default=None,max_length=120),
                    user=Depends(member)):
    """Member-triggered, bounded headline discovery for one ticker.

    GDELT DOC is free and requires no account. One outbound request per press,
    a per-member cooldown, and records are deduplicated by event id so repeated
    presses cannot be used as a scraper.
    """
    global _GDELT_DOWN_UNTIL
    gdelt=_gdelt_module()
    ticker=symbol.strip().upper()
    if not gdelt.SYMBOL_RE.fullmatch(ticker):
        raise HTTPException(422,'Invalid ticker symbol')
    text=(query or f'"{ticker}" (stock OR shares OR earnings)').strip()
    if not gdelt.QUERY_RE.fullmatch(text) or not 3<=len(text)<=120:
        raise HTTPException(422,'Unsupported news query')
    key=(user['id'],ticker)
    now_mono=time.monotonic()
    if _NEWS_SYNC_SEEN.get(key) and now_mono-_NEWS_SYNC_SEEN[key]<300:
        raise HTTPException(429,'That ticker was refreshed moments ago; try again in a few minutes')
    _NEWS_SYNC_SEEN[key]=now_mono
    now=datetime.now(timezone.utc)
    provider,fallback='GDELT DOC (free, no key)',False
    candidates=None
    if time.monotonic()>=_GDELT_DOWN_UNTIL:
        try:
            articles=await asyncio.to_thread(gdelt.fetch_articles,text,max_records=25)
            candidates=gdelt.observe_articles(ticker,text,articles,now)
            examined=len(articles)
        except Exception:
            # GDELT rate-limits shared hosting IPs aggressively (sometimes returning
            # an HTML page with HTTP 200, which fails JSON decoding) and can take many
            # seconds to do it, so back off before retrying.
            _GDELT_DOWN_UNTIL=time.monotonic()+600
            candidates=None
    if candidates is None:
        # The ticker headline feed keeps the radar usable without another credential.
        try:
            candidates=await _yahoo_headlines(ticker,now)
        except Exception as exc:
            raise HTTPException(503,'News discovery unavailable; both GDELT and the headline feed failed') from exc
        provider,fallback,examined='Yahoo Finance headline feed (free, no key)',True,len(candidates)
    stored=0
    for candidate in candidates:
        try: item=Observation(**candidate)
        except ValidationError: continue
        record=item.model_dump(mode='json')
        observed,published=utc(record['observed_at']),utc(record['published_at'])
        if observed>now or published>observed: continue
        await db.kaos_intelligence.update_one(
            {'source':record['source'],'event_id':record['event_id']},{'$set':record},upsert=True)
        stored+=1
    return {'symbol':ticker,'query':text,'articles_examined':examined,'observations_stored':stored,
            'provider':provider,'fallback':fallback,'research_only':True}


async def _yahoo_headlines(ticker,ticker_time):
    """Keyless ticker headline feed used when GDELT refuses the request."""
    import httpx
    from email.utils import parsedate_to_datetime
    from hashlib import sha256
    from xml.etree import ElementTree
    url=f'https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US'
    async with httpx.AsyncClient(timeout=20,follow_redirects=False) as client:
        response=await client.get(url,headers={'User-Agent':'KAOS-Research/3.0'})
        response.raise_for_status()
    if len(response.content)>2_000_000: raise ValueError('Headline feed too large')
    out=[]
    for item in ElementTree.fromstring(response.content).iter('item'):
        title=(item.findtext('title') or '').strip()
        link=(item.findtext('link') or '').strip()
        if not title or not link.startswith('https://') or len(link)>1800: continue
        try: published=parsedate_to_datetime(item.findtext('pubDate') or '')
        except (TypeError,ValueError): continue
        if published.tzinfo is None: published=published.replace(tzinfo=timezone.utc)
        if published>ticker_time or ticker_time-published>timedelta(days=7): continue
        publisher=(item.findtext('source') or 'Yahoo Finance').strip()[:100]
        out.append({'asset':ticker,'asset_class':'stock','source':'news','direction':'neutral','strength':0.25,
                    'event_id':'yahoo-news:'+ticker+':'+sha256(link.encode()).hexdigest()[:24],
                    'observed_at':ticker_time.isoformat(),'published_at':published.isoformat(),
                    'source_url':link,
                    'summary':(f'Yahoo Finance headline for {ticker}: {title[:330]} ({publisher}). '
                               'Headline feed timing is not a verified publication timestamp; '
                               'coverage does not imply price direction.')[:1200]})
        if len(out)>=12: break
    return out

@router.get('/opportunities')
async def opportunities(asset_class: str | None=None,limit:int=Query(30,ge=1,le=100),user=Depends(member)):
    if asset_class and asset_class not in SUPPORTED: raise HTTPException(422,'Unsupported asset class')
    query={'asset_class':asset_class} if asset_class else {}
    # Only bounded recent observations, not the entire historical collection.
    from datetime import timedelta
    cutoff=(datetime.now(timezone.utc)-timedelta(days=7)).isoformat()
    query['observed_at']={'$gte':cutoff}
    records=await db.kaos_intelligence.find(query,{'_id':0}).sort('observed_at',-1).limit(5000).to_list(length=5000)
    groups={}
    for r in records: groups.setdefault((r['asset'],r['asset_class']),[]).append(r)
    ranked=[dict(evaluate(asset,obs),asset_class=kind) for (asset,kind),obs in groups.items()]
    ranked.sort(key=lambda x:x['score'],reverse=True)
    return {'mode':'research_only','coverage':'ingested_sources_only','results':ranked[:limit],
            'scanned_observations':len(records),'note':'Scores are not probabilities or verified trade signals.'}

@router.get('/status')
async def status(user=Depends(member)):
    return {'mode':'research_only','collector_configured':bool(os.getenv('KAOS_COLLECTOR_KEY')),
            'sources':sorted(SOURCES),'asset_classes':sorted(SUPPORTED),'live_feeds_included':False,'collector_available_separately':True}


@router.get('/health')
async def health(user=Depends(member)):
    """Shows sampled feed observation recency, never promises that a provider is live."""
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    records = await db.kaos_intelligence.find(
        {'observed_at': {'$gte': cutoff}},
        {'_id': 0, 'asset_class': 1, 'source': 1, 'event_id': 1, 'observed_at': 1}
    ).sort('observed_at', -1).limit(5000).to_list(length=5000)
    return summarize_health(records)
