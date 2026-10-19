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


class HeadlineScore(BaseModel):
    """Score from an authenticated collector's separately-run financial NLP model."""
    ticker: str = Field(pattern=r"^[A-Za-z0-9._-]{1,20}$")
    asset_class: Literal["stock", "etf", "crypto", "forex"]
    headline: str = Field(min_length=5, max_length=500)
    source_url: str = Field(min_length=12, max_length=2000, pattern=r"^https://")
    published_at: datetime
    score: float = Field(ge=-1, le=1)
    model_id: str = Field(min_length=1, max_length=100)
    model_version: str = Field(min_length=1, max_length=100)


@router.post("/ingest/headline-scores")
async def ingest_headline_scores(items: list[HeadlineScore],
                                 x_kaos_collector_key: str | None = Header(default=None)):
    """Authenticated, attributable sentiment; no autonomous trading authority.

    Server collector must separately verify the original news source and run
    an actual model. A model's output is never represented as a win probability.
    """
    from hashlib import sha256
    from math import isfinite
    from secrets import compare_digest
    from kaos_news_catalysts import aggregate_headlines
    key = os.getenv("KAOS_COLLECTOR_KEY", "")
    if not key or not x_kaos_collector_key or not compare_digest(key, x_kaos_collector_key):
        raise HTTPException(403, "Collector authentication required")
    if not items or len(items) > 100:
        raise HTTPException(422, "Expected 1–100 headline scores")
    now = datetime.now(timezone.utc)
    buckets = {}
    for item in items:
        if not isfinite(item.score):
            raise HTTPException(422, "Finite sentiment score required")
        published = utc(item.published_at)
        if not (now - __import__("datetime").timedelta(hours=24) <= published <= now):
            raise HTTPException(422, "Headline timestamp out of range")
        ticker = item.ticker.upper()
        buckets.setdefault((ticker, item.asset_class), []).append({
            "ticker": ticker, "headline": item.headline,
            "source_url": item.source_url, "published_at": published, "score": item.score,
            "model_id": item.model_id, "model_version": item.model_version})
    written = 0
    summary = []
    for (ticker, asset_class), headlines in buckets.items():
        output = aggregate_headlines(ticker, headlines, now=now)
        # Persist each valid headline separately for audit; the existing radar
        # counts "news" as a single independent source regardless of volume.
        for entry in output["headline_scores"]:
            matching = next(h for h in headlines if h["source_url"] == entry["source_url"]
                            and h["headline"] == entry["headline"])
            identity = "|".join((ticker, entry["source_url"], entry["headline"],
                                  entry["published_at"], matching["model_id"],
                                  matching["model_version"]))
            event_id = "nlp:" + sha256(identity.encode()).hexdigest()
            val = entry["score"]
            observation = {"asset": ticker, "asset_class": asset_class,
                           "source": "news", "event_id": event_id,
                           "direction": "bullish" if val > 0.15 else "bearish" if val < -0.15 else "neutral",
                           "strength": abs(val), "observed_at": now.isoformat(),
                           "published_at": entry["published_at"],
                           "source_url": entry["source_url"],
                           "summary": entry["headline"],
                           "nlp_score": val, "nlp_model_id": matching["model_id"],
                           "nlp_model_version": matching["model_version"],
                           "research_only": True}
            await db.kaos_intelligence.update_one(
                {"source": "news", "event_id": event_id},
                {"$setOnInsert": observation}, upsert=True)
            written += 1
        summary.append({"asset": ticker, "asset_class": asset_class,
                        "valid_headlines": output["sample_count"],
                        "sentiment_mean": output["sentiment_mean"]})
    return {"accepted": written, "markets": summary, "mode": "research_only",
            "trade_execution_enabled": False}


class UnscoredHeadline(BaseModel):
    ticker: str = Field(pattern=r"^[A-Za-z0-9._-]{1,20}$")
    asset_class: Literal["stock", "etf", "crypto", "forex"]
    headline: str = Field(min_length=5, max_length=500)
    source_url: str = Field(min_length=12, max_length=2000, pattern=r"^https://")
    published_at: datetime


@router.post("/ingest/classify-headlines")
async def classify_and_ingest_headlines(
        items: list[UnscoredHeadline],
        x_kaos_collector_key: str | None = Header(default=None)):
    """Run a genuinely provisioned local NLP model, then persist research sentiment.

    This endpoint is collector-only. A missing/unavailable model fails with 503,
    rather than silently substituting pseudo probabilities or synthetic scores.
    """
    from secrets import compare_digest
    from fastapi.concurrency import run_in_threadpool
    from kaos_financial_inference import classify_headlines
    key = os.getenv("KAOS_COLLECTOR_KEY", "")
    if not key or not x_kaos_collector_key or not compare_digest(key, x_kaos_collector_key):
        raise HTTPException(403, "Collector authentication required")
    if not items or len(items) > 100:
        raise HTTPException(422, "Expected 1–100 headlines")
    now = datetime.now(timezone.utc)
    from datetime import timedelta
    for item in items:
        if not now - timedelta(hours=24) <= utc(item.published_at) <= now:
            raise HTTPException(422, "Headline timestamp out of range")
    try:
        predictions = await run_in_threadpool(
            classify_headlines, [item.headline for item in items])
    except (RuntimeError, ImportError, OSError, ValueError) as exc:
        raise HTTPException(503, "Financial NLP model unavailable") from exc
    scored = []
    for item, prediction in zip(items, predictions):
        scored.append(HeadlineScore(
            ticker=item.ticker, asset_class=item.asset_class,
            headline=item.headline, source_url=item.source_url,
            published_at=item.published_at,
            score=prediction["sentiment_score"],
            model_id="trading_hero", model_version=os.getenv(
                "KAOS_TRADING_HERO_MODEL_VERSION", "unversioned-local")))
    return await ingest_headline_scores(scored, x_kaos_collector_key)
