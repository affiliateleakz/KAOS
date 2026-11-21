"""Opt-in cPanel cron runner: one R2 market per invocation, research ONLY.

Suggested hourly cron, separate from FastAPI:
  KAOS_R2_AI_RESEARCH_AUTO_TRAIN=1 /path/to/python apps/api/kaos_r2_ai_cron.py
No cron is installed by this file. Research models never influence live AI.
"""
import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

ROOT=Path(__file__).resolve().parents[2]
load_dotenv(ROOT/".env",override=False)

from db import db, new_id, now_iso
from kaos_r2_market_audit import MARKETS
from kaos_r2_archive import configured,read_archive
from kaos_r2_ai_lab import train_from_candles

async def run(now=None):
    if os.getenv("KAOS_R2_AI_RESEARCH_AUTO_TRAIN")!="1":
        print("KAOS R2 research auto training DISABLED (opt-in required)")
        return 2
    owner=os.getenv("KAOS_CANDLE_OWNER_USER_ID")
    if not owner or not configured():
        print("Owner ID or private R2 reader not configured")
        return 2
    now=now or datetime.now(timezone.utc)
    # UTC hour deterministically rotates all 20 markets; at most one training job
    # on each invocation, protecting shared cPanel CPU and provider limits.
    slot=int(now.timestamp()//3600)
    symbol,asset_class=MARKETS[slot%len(MARKETS)]
    from kaos_r2_archive import ArchiveUnavailable
    try:
        rows,source=await read_archive(symbol,asset_class,60,limit=3000)
        result=await asyncio.to_thread(train_from_candles,rows,60,4)
    except (ArchiveUnavailable,ValueError,RuntimeError,OSError) as exc:
        print(f"{symbol}: R2 training unavailable ({type(exc).__name__})")
        return 1
    if result["status"]=="insufficient_training_history":
        print(f"{symbol}: {result['status']} ({result['samples']} samples)")
        return 0
    fingerprint=result["dataset_fingerprint"]
    prior=await db.kaos_r2_research_models.find_one({
        "owner_id":owner,"symbol":symbol,
        "dataset_fingerprint":fingerprint,
        "horizon_bars":4},{"_id":1})
    if prior:
        print(f"{symbol}: unchanged dataset, no duplicate model")
        return 0
    model=result.pop("model")
    doc={"id":new_id("r2model"),"owner_id":owner,
         "symbol":symbol,"asset_class":asset_class,"source":source,
         "created_at":now_iso(),"status":"candidate",
         "validation_status":result["status"],"research_only":True,
         "execution_enabled":False,"strategy":"R2_OHLC_LOGISTIC_V1",
         "model":model,"trainer":"scheduled_r2_research",**result}
    await db.kaos_r2_research_models.insert_one(dict(doc))
    await db.kaos_r2_research_events.insert_one({
        "model_id":doc["id"],"actor_id":owner,"event":"scheduled_candidate",
        "created_at":now_iso(),"validation_status":result["status"]})
    print(f"{symbol}: saved research candidate {doc['id']} "
          f"status={doc['validation_status']}; NOT deployed")
    return 0

if __name__=="__main__":
    raise SystemExit(asyncio.run(run()))
