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
    from kaos_prediction_validation import evaluate_history
    try:
        return evaluate_history(rows,symbol=symbol,asset_class=asset_class,
                                seconds=seconds,source=next(iter(sources)),
                                horizon=horizon,fee_bps=fee_bps)
    except (ValueError,TypeError) as exc:
        raise HTTPException(422,str(exc)) from exc
