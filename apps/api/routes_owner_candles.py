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

@router.get("/quality")
async def quality(symbol:str=Query(pattern=r"^[A-Z0-9_-]{2,32}$"),
                  asset_class:str=Query("crypto",pattern="^(crypto|stock|forex)$"),
                  seconds:int=Query(60),limit:int=Query(5000,ge=10,le=10000),
                  user=Depends(owner)):
    from kaos_candle_data_quality import audit_candles,chronological_split
    if seconds not in (60,300,900):raise HTTPException(422,"Unsupported timeframe")
    docs=await db.kaos_research_candles.find(
        {"symbol":symbol,"asset_class":asset_class,"seconds":seconds},
        {"_id":0}).sort("ts",-1).limit(limit).to_list(length=limit)
    analysis=audit_candles(docs,seconds)
    splits=chronological_split(analysis.pop("candles"))
    return {"asset_class":asset_class,"symbol":symbol,"seconds":seconds,
      **analysis,"partition_sizes":{k:len(v) for k,v in splits.items()},
      "research_only":True,
      "caution":"Gaps in exchange-closed stock sessions and forex weekends are expected; do not backfill with invented prices."}
