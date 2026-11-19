"""Shared asset research/evidence snapshots for Trending details and discovery."""
import asyncio
import copy
import json
from datetime import datetime,timezone,timedelta
from hashlib import sha256
from types import SimpleNamespace
from fastapi import Depends,HTTPException
from pymongo.errors import DuplicateKeyError
from db import db
from routes_radar import router,Asset,evidence_id,balanced_evidence
from routes_opportunity import member,Observation
from radar_sources import Sources
import radar_settings
import radar_trending
import radar_signals
import kaos_radar_ai as native
from radar_scoring import score

FORMAT='asset-research-v2'
PROVIDERS=('news','sec','government','ethereum')


async def context(assets,budget=12):
    settings=dict(zip(radar_settings.VISIBLE_PROVIDERS,await asyncio.gather(*(radar_settings.settings(p) for p in radar_settings.VISIBLE_PROVIDERS))))
    session=Sources(settings)
    async def cached(provider,asset):
        cfg=settings.get(provider,{})
        key=sha256(json.dumps([provider,asset,cfg],sort_keys=True).encode()).hexdigest()
        now=datetime.now(timezone.utc).timestamp()
        old=await db.kaos_evidence_cache.find_one({'_id':key})
        ttl={'news':300,'sec':3600,'government':3600,'ethereum':60}[provider]
        if old and 0<=now-old.get('checked',0)<(ttl if old['result']['state'] in ('collected','no_matches','not_applicable') else 120):
            return copy.deepcopy(old['result'])
        try:
            await db.kaos_evidence_locks.update_one({'_id':key,'until':{'$lt':now}},{'$set':{'until':now+20}},upsert=True)
        except DuplicateKeyError:
            return {'provider':provider,'asset':asset['symbol'],'asset_class':asset['asset_class'],'state':'collecting','records':[],'observations':None}
        try:
            result=await session.run(provider,asset)
            await db.kaos_evidence_cache.update_one({'_id':key},{'$set':{'checked':now,'result':result,'expires_at':datetime.now(timezone.utc)+timedelta(days=7)}},upsert=True)
            return result
        finally:await db.kaos_evidence_locks.update_one({'_id':key},{'$set':{'until':0}})
    jobs={asyncio.create_task(cached(p,a)):(p,a) for a in assets for p in PROVIDERS}
    results=[]
    try:
        done,pending=await asyncio.wait(jobs,timeout=budget)
        for task in done:
            p,a=jobs[task]
            try:results.append(task.result())
            except Exception:results.append({'provider':p,'asset':a['symbol'],'asset_class':a['asset_class'],'state':'unavailable','records':[],'observations':None})
        for task in pending:
            task.cancel();p,a=jobs[task]
            results.append({'provider':p,'asset':a['symbol'],'asset_class':a['asset_class'],'state':'time_budget','records':[],'observations':None})
    finally:
        for task in jobs:
            if not task.done():task.cancel()
        await asyncio.gather(*jobs,return_exceptions=True)
        await session.close()
    allowed={(a['symbol'],a['asset_class']) for a in assets};valid={};now=datetime.now(timezone.utc)
    cutoff=(now-timedelta(days=7)).isoformat()
    # Per-category bounds keep high-volume news from burying rarer disclosures.
    async def stored(source):
        return await db.kaos_intelligence.find({'asset':{'$in':[a['symbol'] for a in assets]},'source':source,
            'published_at':{'$gte':cutoff}},{'_id':0}).sort('published_at',-1).limit(40).to_list(40)
    from radar_scoring import CHANNEL_NAMES
    historical=await asyncio.gather(*(stored(source) for source in CHANNEL_NAMES))
    incoming=[row for r in results for row in r.get('records',[])]+[row for batch in historical for row in batch]
    for row in incoming:
        try:
            item=Observation(**row).model_dump(mode='json')
            if (item['asset'],item['asset_class']) not in allowed:
                # Options-flow collectors may identify the underlying ticker with
                # asset_class=option. Preserve provenance while scoring its stock.
                target=next((kind for symbol,kind in allowed if symbol==item['asset'] and kind in ('stock','etf')),None)
                related_equity=item['asset_class'] in ('stock','etf')
                underlying_flow=item['source']=='options_flow' and item['asset_class']=='option'
                if target is None or not (related_equity or underlying_flow):continue
                item['original_asset_class']=item['asset_class'];item['asset_class']=target
            published=datetime.fromisoformat(item['published_at']);observed=datetime.fromisoformat(item['observed_at'])
            if not published<=observed<=now:continue
            item.update(provider=str(row.get('provider',item['source']))[:40],id=evidence_id(item))
            valid.setdefault((item['asset'],item['asset_class'],item['id']),item)
        except (ValueError,TypeError):continue
    rows=balanced_evidence(sorted(valid.values(),key=lambda r:r['published_at'],reverse=True),400)
    return {'evidence':rows,'source_status':[{k:v for k,v in r.items() if k!='records'} for r in results]}


def report_key(asset,trending):
    return sha256(json.dumps([FORMAT,native.SCHEMA,asset,trending.get('fetched_at'),trending.get('state'),trending.get('stale')],sort_keys=True).encode()).hexdigest()


async def cached_report(asset,trending):
    now=datetime.now(timezone.utc)
    cached=await db.kaos_asset_reports.find_one({'_id':report_key(asset,trending)})
    if cached and 0<=now.timestamp()-cached.get('checked',0)<300 and cached['report'].get('source_time'):
        try:
            from kaos_opportunity import utc
            if 0<=(now-utc(cached['report']['source_time'])).total_seconds()<1200:return cached['report']
        except (ValueError,TypeError):pass
    return None


async def asset_report(asset,context_data,trending,quote=None):
    now=datetime.now(timezone.utc);planning=bool(quote and quote.get('planning'))
    key=report_key(asset,trending)+(':'+quote['timeframe'] if planning else '')
    old=None if planning else await cached_report(asset,trending)
    if old is not None:return old
    if quote is None:quote=await asyncio.wait_for(radar_signals.market(SimpleNamespace(**asset)),timeout=10)
    await native.ensure_indexes()
    report=await native.assessment(asset,quote,context_data['evidence'],now,trending)
    report['market_snapshot']={k:quote.get(k) for k in ('price','feature_vector','source_time','source','symbol','asset_class','timeframe','planning','horizon')}
    report['scorecard']=score(asset,quote,report,now)
    report['source_status']=[r for r in context_data['source_status'] if r.get('asset')==asset['symbol']]
    # Checked but empty is different from an unconnected source; neither is neutral sentiment.
    mapping={'news':'news','sec':'insider','government':'politician','ethereum':'onchain'}
    for row in report['source_status']:
        source=mapping.get(row.get('provider'))
        item=next((c for c in report['scorecard']['coverage'] if c['source']==source),None)
        if item and item['state']=='missing' and row['state'] in ('no_matches','collected'):item['state']='checked_no_records'
        if item and item['state']=='missing' and row['state']=='not_applicable':item['state']='not_applicable'
    applicable=[c for c in report['scorecard']['coverage'] if c['state']!='not_applicable']
    report['scorecard']['coverage_percent']=round(100*sum(c['state']=='available' for c in applicable)/len(applicable))
    report['scorecard']['context_level']='Broad evidence' if report['scorecard']['coverage_percent']>=60 else 'Limited evidence'
    report['score_version']=FORMAT
    report['research_asof']=now.isoformat()
    await db.kaos_asset_reports.update_one({'_id':key},{'$set':{'checked':now.timestamp(),'report':report,'expires_at':now+timedelta(days=1)}},upsert=True)
    return report


@router.post('/research/asset')
async def research_asset(request:Asset,user=Depends(member)):
    if request.asset_class not in ('stock','etf','crypto','forex'):raise HTTPException(422,'Choose stock, ETF, crypto or forex research')
    asset=request.model_dump()
    # Same public snapshot supplies the list, detail counter, and model input.
    trending=await radar_trending.snapshot()
    old=await cached_report(asset,trending)
    if old is not None:return {'report':old,'trending':trending,'execution_enabled':False}
    stamp=datetime.now(timezone.utc).timestamp()
    try:
        await db.kaos_research_member_limits.update_one({'_id':user['id'],'until':{'$lt':stamp}}, {'$set':{'until':stamp+10}},upsert=True)
    except DuplicateKeyError:raise HTTPException(429,'Wait a few seconds before refreshing stock research.')
    data=await context([asset])
    report=await asset_report(asset,data,trending)
    return {'report':report,'trending':trending,'execution_enabled':False}
