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
                 asset_class:str=Query("crypto",pattern="^(crypto|stock|etf|forex)$"),
                 seconds:int=Query(60),limit:int=Query(1000,ge=1,le=5000),
                 user=Depends(owner)):
    if seconds not in (60,300,900):raise HTTPException(422,"Unsupported timeframe")
    query={"symbol":symbol,"seconds":seconds,"asset_class":asset_class}
    docs=await db.kaos_research_candles.find(query,{"_id":0}).sort("ts",-1).limit(limit).to_list(length=limit)
    rows=list(reversed(docs))
    origin="mongo_continuous_archive"
    from kaos_r2_archive import read_archive, configured, ArchiveUnavailable
    if configured() and len(rows)<limit:
        try:
            r2_rows,_=await read_archive(symbol,asset_class,seconds,limit=max(limit,100))
        except ArchiveUnavailable as exc:
            raise HTTPException(503,"Private R2 archive unavailable") from exc
        if len(r2_rows)>len(rows):
            rows=r2_rows[-limit:]
            origin="cloudflare_r2_private_archive"
    return {"symbol":symbol,"asset_class":asset_class,"seconds":seconds,"candles":rows,
            "candle_origin":origin,
            "source":"Per-candle provider identifiers in each record","research_only":True}


@router.get("/r2-status")
async def r2_archive_status(
    symbol:str=Query("BTC-USD",pattern=r"^[A-Z0-9_.-]{2,32}$"),
    asset_class:str=Query("crypto",pattern="^(crypto|stock|etf|forex)$"),
    seconds:int=Query(60),
    user=Depends(owner),
):
    """Owner-only private R2 connection check. No secret values returned."""
    from kaos_r2_archive import read_archive, configured, ArchiveUnavailable
    if not configured():
        return {"status":"not_configured","r2_connected":False,
                "reason":"R2 S3 credentials not yet configured on KAOS Python API"}
    try:
        rows,source=await read_archive(symbol,asset_class,seconds,limit=300)
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc
    except ArchiveUnavailable:
        return {"status":"read_failed","r2_connected":False,
                "reason":"R2 read failed; verify read-only token and bucket permissions"}
    return {"status":"archive_readable" if rows else "archive_empty",
            "r2_connected":True,"symbol":symbol,"asset_class":asset_class,
            "seconds":seconds,"source":source,"closed_bars":len(rows),
            "last_ts":rows[-1]["ts"] if rows else None,
            "research_only":True,"orders_enabled":False}


@router.get("/r2-structure-replay")
async def r2_structure_replay(
    symbol:str=Query("BTC-USD",pattern=r"^[A-Z0-9_.-]{2,32}$"),
    asset_class:str=Query("crypto",pattern="^(crypto|stock|etf|forex)$"),
    seconds:int=Query(60),
    limit:int=Query(300,ge=100,le=5000),
    expiry_bars:int=Query(4,ge=1,le=240),
    lookback:int=Query(12,ge=5,le=100),
    user=Depends(owner),
):
    """Owner-only historical replay from archived, completed provider candles."""
    from kaos_r2_archive import read_archive, configured, ArchiveUnavailable
    from kaos_r2_research import structure_replay_from_archive
    if not configured():
        raise HTTPException(503,"Private R2 archive not configured")
    try:
        rows,source=await read_archive(symbol,asset_class,seconds,limit=limit)
        result=structure_replay_from_archive(rows,seconds,expiry_bars=expiry_bars,lookback=lookback)
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc
    except ArchiveUnavailable as exc:
        raise HTTPException(503,"Private R2 archive unavailable") from exc
    return {"strategy":"KAOS_STRUCTURE_RESEARCH_V1","symbol":symbol,
            "asset_class":asset_class,"seconds":seconds,"source":source,
            "data_origin":"cloudflare_r2_private_archive",**result}


# ---- Private KAOS R2 website research lab ---------------------------------
# Separate from the legacy deployed model registry and ALL broker order routes.
from pydantic import BaseModel, Field
from typing import Literal
from db import new_id, now_iso
from kaos_r2_market_audit import MARKETS
from kaos_r2_segmented_research import gap_aware_replay
from kaos_r2_ai_lab import train_from_candles

SUPPORTED_MARKETS = {(symbol, kind) for symbol, kind in MARKETS}

class R2LabBacktestRequest(BaseModel):
    symbol: str = Field(default="BTC-USD", max_length=32)
    asset_class: Literal["crypto","stock","etf"] = "crypto"
    limit: int = Field(default=300,ge=100,le=5000)
    expiry_bars: int = Field(default=4,ge=1,le=30)
    lookback: int = Field(default=12,ge=5,le=100)

class R2LabTrainRequest(BaseModel):
    symbol: str = Field(default="BTC-USD",max_length=32)
    asset_class: Literal["crypto","stock","etf"] = "crypto"
    limit: int = Field(default=5000,ge=300,le=5000)
    horizon_bars: int = Field(default=4,ge=1,le=30)

class R2LabPromoteRequest(BaseModel):
    model_id: str = Field(min_length=1,max_length=80)

def _check_market(symbol, asset_class):
    if (symbol,asset_class) not in SUPPORTED_MARKETS:
        raise HTTPException(422,"Market not in configured KAOS R2 collection universe")

async def _r2_market(symbol,asset_class,limit):
    from kaos_r2_archive import read_archive, configured, ArchiveUnavailable
    if not configured():
        raise HTTPException(503,"Private R2 archive not configured")
    try:
        return await read_archive(symbol,asset_class,60,limit=limit)
    except ArchiveUnavailable as exc:
        raise HTTPException(503,"Private R2 archive unavailable") from exc
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc

@router.get("/r2-lab/markets")
async def r2_lab_markets(user=Depends(owner)):
    return {"markets":[{"symbol":s,"asset_class":a} for s,a in MARKETS],
            "strategy":"KAOS_STRUCTURE_RESEARCH_V1",
            "seconds":60,"research_only":True,"execution_enabled":False}

@router.post("/r2-lab/backtest")
async def r2_lab_backtest(req:R2LabBacktestRequest,user=Depends(owner)):
    _check_market(req.symbol,req.asset_class)
    rows,source=await _r2_market(req.symbol,req.asset_class,req.limit)
    try:
        result=gap_aware_replay(rows,60,expiry_bars=req.expiry_bars,lookback=req.lookback)
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc
    record={"id":new_id("r2bt"),"user_id":user["id"],
            "symbol":req.symbol,"asset_class":req.asset_class,
            "source":source,"strategy":"KAOS_STRUCTURE_RESEARCH_V1",
            "timeframe_seconds":60,"expiry_bars":req.expiry_bars,
            "lookback":req.lookback,"request_limit":req.limit,
            "created_at":now_iso(),"research_only":True,
            "execution_enabled":False,
            "profitability_validated":False,
            "history":result["history"],"status":result["status"],
            "summary":result["summary"],"trades":result["trades"],
            "assumptions":"Idealized directional historical results; excludes fees, spread, slippage and payout"}
    await db.kaos_r2_backtest_runs.insert_one(dict(record))
    return record

@router.get("/r2-lab/backtests")
async def r2_lab_backtests(user=Depends(owner)):
    docs=await db.kaos_r2_backtest_runs.find(
        {"user_id":user["id"]},
        {"_id":0,"trades":0}).sort("created_at",-1).limit(30).to_list(length=30)
    return {"runs":docs,"research_only":True}

@router.post("/r2-lab/train")
async def r2_lab_train(req:R2LabTrainRequest,user=Depends(owner)):
    _check_market(req.symbol,req.asset_class)
    rows,source=await _r2_market(req.symbol,req.asset_class,req.limit)
    # Bounded CPU fitting off the async event loop.
    import asyncio
    try:
        result=await asyncio.to_thread(train_from_candles,rows,60,req.horizon_bars)
    except (ValueError,ZeroDivisionError,OverflowError) as exc:
        raise HTTPException(422,"R2 training data failed validation") from exc
    if result["status"]=="insufficient_training_history":
        return {"ok":False,**result,"symbol":req.symbol,"asset_class":req.asset_class}
    model=result.pop("model")
    record={"id":new_id("r2model"),"owner_id":user["id"],
            "symbol":req.symbol,"asset_class":req.asset_class,
            "source":source,"created_at":now_iso(),
            "status":"candidate","validation_status":result["status"],
            "research_only":True,"execution_enabled":False,
            "strategy":"R2_OHLC_LOGISTIC_V1","model":model,**result}
    # Model kept in separate research collection; NEVER part of live inference.
    await db.kaos_r2_research_models.insert_one(dict(record))
    await db.kaos_r2_research_events.insert_one({
        "model_id":record["id"],"actor_id":user["id"],
        "event":"trained_candidate","created_at":now_iso(),
        "validation_status":record["validation_status"]})
    return {"ok":True,**{k:v for k,v in record.items() if k not in ("_id","model","test_predictions")}}

@router.get("/r2-lab/models")
async def r2_lab_models(user=Depends(owner)):
    docs=await db.kaos_r2_research_models.find(
        {"owner_id":user["id"]},
        {"_id":0,"model":0,"test_predictions":0}).sort("created_at",-1).limit(30).to_list(length=30)
    return {"models":docs,"research_only":True,"execution_enabled":False}

@router.post("/r2-lab/promote")
async def r2_lab_promote(req:R2LabPromoteRequest,user=Depends(owner)):
    doc=await db.kaos_r2_research_models.find_one({"id":req.model_id,"owner_id":user["id"]})
    if not doc:
        raise HTTPException(404,"Research model not found")
    if doc.get("validation_status")!="validated_research_candidate" or doc.get("promotion_blockers"):
        raise HTTPException(409,"Research candidate failed holdout validation; promotion blocked")
    if doc.get("status") not in ("candidate","research_active"):
        raise HTTPException(409,"Research model is not promotable")
    # No effect on db.ai_models, /api/v1/ai/predict, licenses or execution.
    await db.kaos_r2_research_models.update_many(
        {"owner_id":user["id"],"status":"research_active"},
        {"$set":{"status":"candidate"}})
    await db.kaos_r2_research_models.update_one(
        {"id":req.model_id,"owner_id":user["id"],"validation_status":"validated_research_candidate"},
        {"$set":{"status":"research_active","promoted_at":now_iso()}})
    await db.kaos_r2_research_events.insert_one(
        {"model_id":req.model_id,"actor_id":user["id"],
         "event":"research_promoted","created_at":now_iso(),
         "execution_enabled":False})
    return {"ok":True,"model_id":req.model_id,"status":"research_active",
            "live_trading_enabled":False,"production_ai_changed":False}
