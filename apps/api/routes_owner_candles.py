"""Owner-only candle research status and export. Collection runs as a separate worker."""
import os
from fastapi import APIRouter,Depends,HTTPException,Query
from auth import get_current_user
from db import db

router=APIRouter(prefix="/api/v1/owner/candles",tags=["owner-research"])

def require_owner(user):
    owner=os.getenv("KAOS_CANDLE_OWNER_USER_ID","")
    if not owner or user.get("id")!=owner or user.get("role") not in ("admin","super_admin"):
        raise HTTPException(403,"Private research owner only")
    return user

async def owner(user=Depends(get_current_user)):
    return require_owner(user)

@router.get("/status")
async def status(user=Depends(owner)):
    state=await db.kaos_candle_collector_state.find_one({"_id":"coinbase_worker"},{"_id":0})
    pairs=await db.kaos_research_candles.distinct("symbol")
    result=[]
    for symbol in pairs[:30]:
        count=await db.kaos_research_candles.count_documents({"symbol":symbol})
        latest=await db.kaos_research_candles.find_one({"symbol":symbol},{"_id":0},sort=[("ts",-1)])
        result.append({"symbol":symbol,"candles":count,"last_ts":latest.get("ts") if latest else None})
    return {"state":state,"markets":result,"research_only":True,"orders_enabled":False}

@router.get("/export")
async def export(symbol:str=Query(pattern=r"^[A-Z0-9_-]{2,32}$"),
                 asset_class:str=Query("crypto",pattern="^(crypto|stock|forex)$"),
                 seconds:int=Query(60),limit:int=Query(1000,ge=1,le=5000),
                 user=Depends(owner)):
    if seconds not in (60,300,900):raise HTTPException(422,"Unsupported timeframe")
    query={"symbol":symbol,"seconds":seconds,"asset_class":asset_class}
    docs=await db.kaos_research_candles.find(query,{"_id":0}).sort("ts",-1).limit(limit).to_list(length=limit)
    return {"symbol":symbol,"asset_class":asset_class,"seconds":seconds,"candles":list(reversed(docs)),
            "source":"Per-candle provider identifiers in each record","research_only":True}


@router.get("/validate-direction")
async def validate_direction(symbol:str=Query(pattern=r"^[A-Z0-9_-]{2,32}$"),
                             asset_class:str=Query("crypto",pattern="^(crypto|stock|forex)$"),
                             seconds:int=Query(60),horizon:int=Query(5,ge=1,le=60),
                             fee_bps:float=Query(10.0,ge=0,le=250),
                             include_intelligence:bool=False,
                             user=Depends(owner)):
    """Owner-only chronological research validation of an archived market.

    Only one provider is permitted in each run; samples don't cross sources.
    This does NOT request new data, train a model or enable orders.
    """
    if seconds not in (60,300,900):
        raise HTTPException(422,"Unsupported timeframe")
    rows=await db.kaos_research_candles.find(
        {"symbol":symbol,"asset_class":asset_class,"seconds":seconds},
        {"_id":0}).sort("ts",-1).limit(5000).to_list(length=5000)
    rows.reverse()
    if not rows:
        return {"status":"insufficient_archived_history","decision_count":0,
                "research_only":True,"options_validated":False,
                "reason":"No archived candles for the specified market and timeframe"}
    sources={r.get("source") for r in rows}
    if len(sources)!=1 or not all(sources):
        raise HTTPException(409,"Mixed or missing historical price providers; use a single trusted source")
    observations=None
    if include_intelligence:
        # Capture ONLY already-stored observations with their original observed
        # and published timestamps. Do not re-fetch today's news during replay.
        # Limit volume to avoid unbounded DB reads and computation.
        first=rows[0]["ts"]
        from datetime import datetime,timezone,timedelta
        from_ts=datetime.fromtimestamp(first/1000,timezone.utc)-timedelta(days=7)
        observations=await db.kaos_intelligence.find(
            {"asset":symbol,"asset_class":asset_class,
             "observed_at":{"$gte":from_ts.isoformat()}},
            {"_id":0,"asset":1,"asset_class":1,"event_id":1,"source":1,
             "observed_at":1,"published_at":1,"strength":1,"direction":1}
        ).sort("observed_at",1).limit(5000).to_list(length=5000)
    from kaos_prediction_validation import evaluate_history
    try:
        return evaluate_history(rows,symbol=symbol,asset_class=asset_class,
                                seconds=seconds,source=next(iter(sources)),
                                horizon=horizon,fee_bps=fee_bps,
                                observations=observations)
    except (ValueError,TypeError) as exc:
        raise HTTPException(422,str(exc)) from exc


@router.get("/evaluate-multifactor")
async def evaluate_multifactor(symbol:str=Query(pattern=r"^[A-Z0-9_-]{2,32}$"),
                               asset_class:str=Query("crypto",pattern="^(crypto|stock|forex)$"),
                               seconds:int=Query(60),
                               horizon:int=Query(5,ge=1,le=30),
                               fee_bps:float=Query(10.0,ge=0,le=250),
                               user=Depends(owner)):
    """Owner-only offline fitted baseline on existing single-source archives.

    Returns held-out descriptive metrics, never a trained production model.
    Bounded query; no model weights persisted and no quote/broker network call.
    """
    if seconds not in (60,300,900):
        raise HTTPException(422,"Unsupported timeframe")
    rows=await db.kaos_research_candles.find(
        {"symbol":symbol,"asset_class":asset_class,"seconds":seconds},
        {"_id":0}).sort("ts",-1).limit(5000).to_list(5000)
    rows.reverse()
    if not rows:
        return {"status":"insufficient_point_in_time_training_data","samples":0,
                "research_only":True,"model_trained":False,"options_validated":False}
    sources={r.get("source") for r in rows}
    if len(sources)!=1 or not all(sources):
        raise HTTPException(409,"Mixed or missing candle providers: model requires one source")
    from datetime import datetime,timezone,timedelta
    cutoff=(datetime.fromtimestamp(rows[0]["ts"]/1000,timezone.utc)-
            timedelta(days=7)).isoformat()
    evidence=await db.kaos_intelligence.find(
        {"asset":symbol,"asset_class":asset_class,"observed_at":{"$gte":cutoff}},
        {"_id":0,"asset":1,"asset_class":1,"event_id":1,"source":1,
         "observed_at":1,"published_at":1,"strength":1,"direction":1}
    ).sort("observed_at",1).limit(5000).to_list(5000)
    from kaos_multifactor_baseline import evaluate
    try:
        return evaluate(rows,evidence,symbol=symbol,asset_class=asset_class,
                        seconds=seconds,source=next(iter(sources)),
                        horizon=horizon,cost_bps=fee_bps)
    except (ValueError,TypeError,OverflowError) as exc:
        raise HTTPException(422,str(exc)) from exc


@router.get("/walk-forward")
async def walk_forward_research(symbol:str=Query(pattern=r"^[A-Z0-9_-]{2,32}$"),
                                asset_class:str=Query("crypto",pattern="^(crypto|stock|forex)$"),
                                seconds:int=Query(60),horizon:int=Query(5,ge=1,le=30),
                                folds:int=Query(3,ge=2,le=5),
                                cost_bps:float=Query(10.0,ge=0,le=250),
                                user=Depends(owner)):
    """Owner-only multi-period offline evaluation, no persisted weights/orders."""
    if seconds not in (60,300,900):
        raise HTTPException(422,"Unsupported interval")
    rows=await db.kaos_research_candles.find(
        {"symbol":symbol,"asset_class":asset_class,"seconds":seconds},
        {"_id":0}).sort("ts",-1).limit(5000).to_list(5000)
    rows.reverse()
    if not rows:
        return {"status":"insufficient_walk_forward_history","samples":0,
                "research_only":True,"orders_enabled":False}
    sources={r.get("source") for r in rows}
    if len(sources)!=1 or not all(sources):
        raise HTTPException(409,"Use a single price feed for this research evaluation")
    from datetime import datetime,timezone,timedelta
    cutoff=(datetime.fromtimestamp(rows[0]["ts"]/1000,timezone.utc)-
            timedelta(days=7)).isoformat()
    observations=await db.kaos_intelligence.find(
        {"asset":symbol,"asset_class":asset_class,"observed_at":{"$gte":cutoff}},
        {"_id":0,"asset":1,"asset_class":1,"event_id":1,"source":1,
         "observed_at":1,"published_at":1,"strength":1,"direction":1}
    ).sort("observed_at",1).limit(5000).to_list(5000)
    from kaos_walk_forward import walk_forward
    try:
        return walk_forward(rows,observations,symbol=symbol,
            asset_class=asset_class,seconds=seconds,source=next(iter(sources)),
            horizon=horizon,cost_bps=cost_bps,folds=folds)
    except (ValueError,TypeError,OverflowError) as exc:
        raise HTTPException(422,str(exc)) from exc


@router.get("/readiness")
async def archive_readiness(symbol:str=Query(pattern=r"^[A-Z0-9_-]{2,32}$"),
                            asset_class:str=Query("crypto",pattern="^(crypto|stock|forex)$"),
                            seconds:int=Query(60),
                            user=Depends(owner)):
    """Owner-only market archive readiness and evidence coverage diagnosis."""
    if seconds not in (60,300,900):
        raise HTTPException(422,"Unsupported timeframe")
    candles=await db.kaos_research_candles.find(
        {"symbol":symbol,"asset_class":asset_class,"seconds":seconds},
        {"_id":0}).sort("ts",-1).limit(5000).to_list(5000)
    candles.reverse()
    from datetime import datetime,timezone,timedelta
    lower=(datetime.fromtimestamp(candles[0]["ts"]/1000,timezone.utc)-
           timedelta(days=7)).isoformat() if candles else (
           datetime.now(timezone.utc)-timedelta(days=7)).isoformat()
    obs=await db.kaos_intelligence.find(
        {"asset":symbol,"asset_class":asset_class,"observed_at":{"$gte":lower}},
        {"_id":0,"asset":1,"asset_class":1,"event_id":1,"source":1,
         "observed_at":1,"published_at":1,"strength":1,"direction":1}
    ).sort("observed_at",1).limit(5000).to_list(5000)
    from kaos_archive_readiness import inspect_market
    try:
        return inspect_market(candles,obs,symbol=symbol,
                              asset_class=asset_class,seconds=seconds)
    except (ValueError,TypeError,OverflowError) as exc:
        raise HTTPException(422,str(exc)) from exc


@router.post("/prediction-candidates/build")
async def build_prediction_candidate(symbol:str=Query(pattern=r"^[A-Z0-9_-]{2,32}$"),
                                    asset_class:str=Query("crypto",pattern="^(crypto|stock|forex)$"),
                                    seconds:int=Query(60),horizon:int=Query(5,ge=1,le=30),
                                    fee_bps:float=Query(10.,ge=0,le=250),
                                    user=Depends(owner)):
    """Owner-only fit and research screening; never activate on training."""
    if seconds not in (60,300,900):
        raise HTTPException(422,"Unsupported timeframe")
    rows=await db.kaos_research_candles.find(
        {"symbol":symbol,"asset_class":asset_class,"seconds":seconds},
        {"_id":0}).sort("ts",-1).limit(5000).to_list(5000)
    rows.reverse()
    sources={r.get("source") for r in rows}
    if len(sources)!=1 or not all(sources):
        return {"status":"insufficient_data","candidate":None,
                "reason":"No complete single-provider archive"}
    from datetime import datetime,timezone,timedelta
    cutoff=(datetime.fromtimestamp(rows[0]["ts"]/1000,timezone.utc)-timedelta(days=7)).isoformat()
    evidence=await db.kaos_intelligence.find(
        {"asset":symbol,"asset_class":asset_class,"observed_at":{"$gte":cutoff}},
        {"_id":0,"asset":1,"asset_class":1,"event_id":1,"source":1,
         "observed_at":1,"published_at":1,"strength":1,"direction":1}
    ).sort("observed_at",1).limit(5000).to_list(5000)
    from kaos_active_research_prediction import build_candidate
    try:
        result=build_candidate(rows,evidence,symbol=symbol,asset_class=asset_class,
                               seconds=seconds,source=next(iter(sources)),
                               horizon=horizon,cost_bps=fee_bps)
    except (ValueError,TypeError,OverflowError) as exc:
        raise HTTPException(422,str(exc)) from exc
    candidate=result["candidate"]
    if candidate:
        from datetime import datetime,timezone
        candidate["approved"]=False
        candidate["created_at"]=datetime.now(timezone.utc).isoformat()
        await db.kaos_research_prediction_candidates.update_one(
            {"_id":candidate["model_digest"]},
            {"$set":{**candidate,"owner_id":str(user["id"])}},upsert=True)
    return {**result,"candidate":None if candidate is None else {
        k:v for k,v in candidate.items() if k!="model"},
        "approval_required":True,"orders_enabled":False}


@router.post("/prediction-candidates/approve")
async def approve_prediction_candidate(model_digest:str=Query(pattern=r"^[0-9a-f]{64}$"),
                                       user=Depends(owner)):
    """Explicit owner approval of only pre-screened archived research models."""
    candidate=await db.kaos_research_prediction_candidates.find_one({"_id":model_digest})
    if not candidate:
        raise HTTPException(404,"Unknown model candidate")
    if not candidate.get("quality_screen_pass") or candidate.get("model_digest")!=model_digest:
        raise HTTPException(409,"Candidate failed quality screen")
    # Stable exact-identity key; approval of one market doesn't authorize other
    # markets, timeframes, feeds or forecast horizons.
    key=f"{candidate['asset_class']}:{candidate['symbol']}:{candidate['seconds']}"
    from datetime import datetime,timezone
    await db.kaos_research_prediction_active.update_one({"_id":key},
        {"$set":{"approved":True,"approved_by":str(user["id"]),
                 "approved_at":datetime.now(timezone.utc).isoformat(),
                 "model_digest":model_digest,
                 "artifact":{k:v for k,v in candidate.items() if k not in ("_id","owner_id")}}},
        upsert=True)
    return {"status":"experimental_research_model_approved","key":key,
            "model_digest":model_digest,"orders_enabled":False,
            "note":"Approval enables advisory experiments only; never live options or order execution"}
