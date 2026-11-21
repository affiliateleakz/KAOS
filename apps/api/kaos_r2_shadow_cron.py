"""Opt-in KAOS R2 shadow prediction runner. No broker, no orders.

Use cPanel every five minutes only after R2 and Mongo credentials are verified:
KAOS_R2_SHADOW_PREDICT_ENABLED=1 <python> apps/api/kaos_r2_shadow_cron.py
One prediction per saved model and closed candle. Future outcomes are
reconciled on later runs from the SAME source's closed R2 candles.
"""
import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[2]/".env",override=False)

from db import db, now_iso
from kaos_r2_archive import read_archive, configured, ArchiveUnavailable
from kaos_r2_market_audit import MARKETS
from kaos_r2_shadow_predict import prediction, settle
from kaos_ai_evidence_features import make_feature_snapshot
from datetime import datetime, timezone

async def _market(symbol,asset_class):
    # Only act on existing fitted candidates, NEVER fabricate a trained model.
    model=await db.kaos_r2_research_models.find_one(
        {"symbol":symbol,"asset_class":asset_class,
         "research_only":True,"execution_enabled":False,
         "status":{"$in":["research_active","candidate"]},
         "model.schema":"kaos_r2_ohlc_logistic_v1"},
        {"_id":0},sort=[("created_at",-1)])
    if model is None:
        return {"symbol":symbol,"status":"no_trained_model"}
    rows,source=await read_archive(symbol,asset_class,60,limit=300)
    if not rows:
        return {"symbol":symbol,"status":"no_r2_candles"}
    # Settle old predictions first so candidate results do not rely on trades.
    cursor=db.kaos_r2_shadow_predictions.find(
        {"symbol":symbol,"asset_class":asset_class,
         "source":source,"outcome_status":"pending"},
        {"_id":0}).sort("observed_ts",-1).limit(120)
    pending=await cursor.to_list(length=120)
    settled=0
    for prior in pending:
        result=settle(prior,rows)
        if result:
            updated=await db.kaos_r2_shadow_predictions.update_one(
                {"id":prior["id"],"outcome_status":"pending"},
                {"$set":{**result,"settled_at":now_iso()}})
            settled+=updated.modified_count
    # New observations are collected independent of whether any market order
    # has ever been placed. Staleness/non-contiguity fails closed.
    try:
        forecast=prediction(rows,symbol=symbol,asset_class=asset_class,
                            seconds=60,source=source,record=model)
    except ValueError as exc:
        return {"symbol":symbol,"status":"no_eligible_forecast",
                "reason":str(exc),"new_settlements":settled}
    # Attach an immutable evidence snapshot at the exact forecast decision
    # cutoff. This is NOT an intelligence-trained model and does not change
    # the OHLC-only forecast direction or its probability.
    cutoff=datetime.fromtimestamp(forecast["candle_end_ts"]/1000,timezone.utc)
    start=cutoff.replace(microsecond=0)
    from datetime import timedelta
    min_iso=(start-timedelta(days=90)).isoformat()
    end_iso=cutoff.isoformat()
    evidence=await db.kaos_intelligence.find(
        {"asset":symbol,"asset_class":asset_class,
         "observed_at":{"$gte":min_iso,"$lte":end_iso}},
        {"_id":0,"asset":1,"asset_class":1,"source":1,
         "event_id":1,"provider":1,"direction":1,"strength":1,
         "observed_at":1,"published_at":1,"event_at":1}
    ).sort("observed_at",-1).limit(5000).to_list(length=5000)
    snapshot=make_feature_snapshot(
        symbol=symbol,asset_class=asset_class,decision_at=cutoff,
        observations=evidence,candle_source=source,candle_end_at=cutoff)
    forecast["evidence_context"]={
        "schema":snapshot["schema"],
        "decision_at":snapshot["decision_at"],
        "source_coverage":snapshot["source_coverage"],
        "categories":snapshot["categories"],
        "rejected":snapshot["rejected"],
        "affects_direction":False,
        "trained_on_intelligence":False,
        "research_only":True,
    }
    import hashlib
    forecast["id"]=hashlib.sha256(
        f'{model["id"]}|{symbol}|{source}|{forecast["observed_ts"]}|{forecast["horizon_bars"]}'.encode()
    ).hexdigest()[:40]
    forecast["created_at"]=now_iso()
    # Unique upsert means each model/candle gets at most one prediction.
    result=await db.kaos_r2_shadow_predictions.update_one(
        {"id":forecast["id"]},{"$setOnInsert":forecast},upsert=True)
    return {"symbol":symbol,"status":"shadow_prediction",
            "direction":forecast["direction"],"model_id":model["id"],
            "new":bool(result.upserted_id),"new_settlements":settled}

async def run():
    if os.getenv("KAOS_R2_SHADOW_PREDICT_ENABLED")!="1":
        print("KAOS shadow prediction DISABLED (requires explicit opt-in)")
        return 2
    if not configured() or not os.getenv("KAOS_CANDLE_OWNER_USER_ID"):
        print("KAOS R2 or owner not configured")
        return 2
    semaphore=asyncio.Semaphore(3)
    async def bounded(market):
        async with semaphore:
            try:
                return await _market(*market)
            except (ArchiveUnavailable,ValueError,RuntimeError,OSError) as exc:
                return {"symbol":market[0],"status":"error","reason":type(exc).__name__}
    results=await asyncio.gather(*(bounded(market) for market in MARKETS))
    for result in results:
        print(result)
    failures=[r for r in results if r["status"]=="error"]
    print(f"KAOS SHADOW: markets={len(results)}, failures={len(failures)}, orders=0")
    return 1 if failures else 0

if __name__=="__main__":
    raise SystemExit(asyncio.run(run()))
