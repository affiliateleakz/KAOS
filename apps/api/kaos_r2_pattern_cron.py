"""Private R2 pattern observing cron: market activity, not trade activity.

Enable with KAOS_R2_PATTERN_OBSERVER_ENABLED=1. On each invocation it
processes all configured 20 markets, reads only R2 and writes Mongo research
observations; no AI model promotion or broker execution.

cPanel cron (every 5 minutes):
  */5 * * * * KAOS_R2_PATTERN_OBSERVER_ENABLED=1 /path/python /path/apps/api/kaos_r2_pattern_cron.py >> /private/log 2>&1
"""
import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

from dotenv import load_dotenv

ROOT=Path(__file__).resolve().parents[2]
load_dotenv(ROOT/".env",override=False)

from db import db, now_iso
from kaos_r2_archive import configured,read_archive,ArchiveUnavailable
from kaos_r2_market_audit import MARKETS
from kaos_r2_pattern_observer import observe_market

async def run():
    if os.getenv("KAOS_R2_PATTERN_OBSERVER_ENABLED")!="1":
        print("R2 pattern observer DISABLED; enable explicitly in cron")
        return 2
    if not configured():
        print("R2 is not configured")
        return 2
    semaphore=asyncio.Semaphore(3)
    async def inspect(symbol,asset_class):
        async with semaphore:
            try:
                rows,source=await read_archive(symbol,asset_class,60,limit=300)
                if not rows:
                    return {"market":symbol,"status":"no_candles"}
                report=await asyncio.to_thread(observe_market,rows,symbol,asset_class,60,source)
                from pymongo import UpdateOne
                updates=[]
                for evt in report["events"]:
                    # Stable observations keyed by source/time/pattern, never by trades.
                    # Future settlement updates are monotonic: once known, they remain
                    # immutable across subsequent collection runs.
                    # Note source OHLC archives are first-version immutable.
                    updates.append(UpdateOne(
                        {"id":evt["id"]},
                        {"$setOnInsert":{k:v for k,v in evt.items() if k!="horizons"}},
                        upsert=True))
                if updates:
                    await db.kaos_r2_pattern_observations.bulk_write(updates,ordered=False)
                settled=0
                for evt in report["events"]:
                    for horizon in evt["horizons"]:
                        if horizon["status"]!="settled":
                            continue
                        # New fields only; no overwrite of previous confirmed outcomes.
                        h=horizon["horizon_bars"]
                        key="outcomes."+str(h)
                        r=await db.kaos_r2_pattern_observations.update_one(
                            {"id":evt["id"],key:{"$exists":False}},
                            {"$set":{key:h}})
                        settled+=r.modified_count
                await db.kaos_r2_pattern_market_state.update_one(
                    {"symbol":symbol,"asset_class":asset_class,"seconds":60},
                    {"$set":{"status":"observing","last_observed_candle_ts":rows[-1]["ts"],
                             "pattern_counts_snapshot":report["pattern_counts"],
                             "archive_bars":len(rows),"segments":report["segments"],
                             "source":source,"observed_at":now_iso()}},upsert=True)
                return {"market":symbol,"status":"observed","bars":len(rows),
                        "detections_in_window":report["events_count"],
                        "new_settlements":settled}
            except (ArchiveUnavailable,RuntimeError,ValueError,OSError) as exc:
                return {"market":symbol,"status":"error","reason":type(exc).__name__}
    results=await asyncio.gather(*(inspect(*m) for m in MARKETS))
    for item in results:
        print(item)
    ok=sum(x["status"]=="observed" for x in results)
    print(f"KAOS pattern observer: {ok}/{len(MARKETS)} markets; no trades placed")
    return 0 if ok==len(MARKETS) else 1

if __name__=="__main__":
    raise SystemExit(asyncio.run(run()))
