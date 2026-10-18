"""Research-only KAOS Opportunity Radar API. Collector requires server-side token."""
import os
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Literal
from auth import get_current_user
from db import db
from services_trading import get_entitlements
from kaos_opportunity import evaluate, SUPPORTED, SOURCES, utc
from kaos_source_health import summarize_health

router=APIRouter(prefix='/api/v1/intelligence',tags=['opportunity-radar'])

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
