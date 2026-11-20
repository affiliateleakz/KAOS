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
