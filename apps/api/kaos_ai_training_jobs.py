"""Persistent, bounded one-click KAOS R2 market training worker.

The UI enqueues a job. A separate cPanel cron worker consumes 2 markets per
invocation, checkpointing each market in Mongo so Apache/Passenger request
timeouts cannot erase a multi-market training run. No order or live inference
authorization. No news/social/insider features are invented from OHLCV.
"""
import asyncio
import os
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from pathlib import Path
from dotenv import load_dotenv

# Ensure cPanel cron has identical env lookup to Passenger before db imports.
load_dotenv(Path(__file__).resolve().parents[2]/".env",override=False)

from db import db, new_id, now_iso
from kaos_r2_archive import read_archive, configured, ArchiveUnavailable
from kaos_r2_market_audit import MARKETS
from kaos_r2_ai_lab import train_from_candles

JOB_COLLECTION="kaos_r2_train_jobs"
MAX_PENDING_JOBS=2
MAX_MARKETS_PER_TICK=2
LEASE_MINUTES=10
VALID_HORIZONS={1,2,3,4,5,10,15,30}
SOURCES=(
    ("r2_ohlcv","Historical candles + volume"),
    ("candlestick_features","Candle structure/volume changes (derived from R2)"),
    ("news","Timestamped company and market news"),
    ("social","Timestamped social mentions and sentiment"),
    ("insider_trades","Insider filings and transaction dates"),
    ("institutional_trades","Institutional ownership and reported transactions"),
    ("short_interest","Short interest/borrow and squeeze metrics"),
    ("options_flow","Options flow and open interest"),
    ("macro_events","Economic calendar releases"),
    ("supply_demand","Historical support/resistance and demand zones"),
    ("pattern_observer","Archived chart pattern observations"),
    ("filings","Historical regulatory filings"),
    ("politician_trades","Congressional trade disclosures"),
    ("onchain","Timestamped on-chain activity"),
    ("dark_pool","Dark pool trading observations"),
    ("liquidity","Market liquidity observations"),
    ("technical_context","Externally ingested technical observations"),
)
TRAINED_FEATURES=(
    "ret1","ret3","ret8","range","body",
    "upper_wick","lower_wick","volume_change",
)

def source_report(*, archive_status="pending",archive_rows=0,source=None):
    """Auditable manifest: absent source != trained source."""
    sources=[]
    for key,label in SOURCES:
        used=key in ("r2_ohlcv","candlestick_features") and archive_status=="ready"
        sources.append({
            "key":key,"label":label,
            "status":"trained" if used else (
                "available_not_trained" if key in ("r2_ohlcv","candlestick_features") and archive_status=="available" else
                "missing" if key in ("r2_ohlcv","candlestick_features") and archive_status=="missing" else
                "pending" if key in ("r2_ohlcv","candlestick_features") else "not_integrated"),
            "used_in_training":bool(used),
            "rows":archive_rows if key=="r2_ohlcv" else None,
            "provider":source if key=="r2_ohlcv" else None,
        })
    return sources

def market_selection(scope,symbol=None):
    if scope=="all":
        return [{"symbol":s,"asset_class":a} for s,a in MARKETS]
    if scope!="single" or not isinstance(symbol,str):
        raise ValueError("Invalid AI training scope")
    match=next(((s,a) for s,a in MARKETS if s==symbol),None)
    if not match:raise ValueError("Market not in R2 training universe")
    return [{"symbol":match[0],"asset_class":match[1]}]

def initial_job(owner_id,scope,symbol,limit,horizon):
    if not isinstance(owner_id,str) or not owner_id:
        raise ValueError("Owner required")
    if not isinstance(limit,int) or isinstance(limit,bool) or not 300<=limit<=5000:
        raise ValueError("Invalid training history limit")
    if horizon not in VALID_HORIZONS or isinstance(horizon,bool):
        raise ValueError("Unsupported model horizon")
    markets=market_selection(scope,symbol)
    now=now_iso()
    return {
        "_id":new_id("train"),
        "owner_id":owner_id,"scope":scope,"horizon_bars":horizon,
        "history_limit":limit,
        "status":"queued","created_at":now,"updated_at":now,
        "next_index":0,"total":len(markets),"completed":0,
        "trained":0,"reused":0,"not_validated":0,"failed":0,
        "markets":markets,"results":[],
        "lease_until":datetime.fromtimestamp(0,timezone.utc),
        "worker_token":None,
        "research_only":True,"execution_enabled":False,
        "model_family":"kaos_r2_ohlc_logistic_v1",
        "trained_feature_names":list(TRAINED_FEATURES),
        "feature_sources_manifest":source_report(),
        "other_sources_enabled":False,\n        "enrichment_attempt_available":True,
        "note":"Closed R2 OHLCV feeds the primary model; eligible already-ingested time-safe intelligence may separately train an enriched RESEARCH model. Per-market coverage states which categories actually trained. Other categories remain unavailable."
    }

def public_job(job):
    if job is None:return None
    keys=("id","scope","status","created_at","updated_at","total","completed",
          "trained","reused","not_validated","failed","next_index","markets",
          "results","model_family","trained_feature_names",
          "feature_sources_manifest","other_sources_enabled",\n          "enrichment_attempt_available","research_only",
          "execution_enabled","note","horizon_bars","history_limit")
    result={k:job.get("_id") if k=="id" else job.get(k) for k in keys}
    result["orders_enabled"]=False
    return result

async def try_enriched_intelligence(job,market,rows,source):
    """Fit an additional research model ONLY with verified as-of evidence."""
    from kaos_ai_intelligence_training import (
        train_enriched,MAX_RECORDS,SCHEMA,FEATURE_NAMES
    )
    symbol=market["symbol"]
    asset_class=market["asset_class"]
    try:
        observations=await db.kaos_intelligence.find(
            {"asset":symbol,"asset_class":asset_class},
            {"_id":0,"event_id":1,"asset":1,"asset_class":1,
             "source":1,"direction":1,"strength":1,
             "observed_at":1,"published_at":1}
        ).sort("observed_at",1).limit(MAX_RECORDS+1).to_list(length=MAX_RECORDS+1)
    except Exception as exc:
        return {"status":"source_unavailable","reason":type(exc).__name__}
    if len(observations)>MAX_RECORDS:
        return {"status":"source_history_truncated",
                "reason":"Historical intelligence records exceed safe audit limit"}
    try:
        report=await asyncio.to_thread(
            train_enriched,rows,observations,
            symbol=symbol,asset_class=asset_class,seconds=60,
            horizon=job["horizon_bars"])
    except (ValueError,RuntimeError,OverflowError,ZeroDivisionError) as exc:
        return {"status":"not_trained","reason":type(exc).__name__}
    coverage=report.get("coverage",{})
    if report["status"] in ("insufficient_history","insufficient_external_history"):
        return {"status":report["status"],"coverage":coverage,
                "reason":report.get("reason","Not enough historically available evidence")}
    model=report.pop("model")
    fingerprint=report["dataset_fingerprint"]
    existing=await db.kaos_r2_research_models.find_one(
        {"owner_id":job["owner_id"],"symbol":symbol,"asset_class":asset_class,
         "source":source,"horizon_bars":job["horizon_bars"],
         "dataset_fingerprint":fingerprint,"model.schema":SCHEMA},
        {"id":1,"_id":0})
    if existing:
        return {"status":"reused","model_id":existing["id"],
                "source_categories":report["source_categories_in_training"],
                "coverage":coverage}
    document={
        "id":new_id("r2enriched"),"owner_id":job["owner_id"],
        "symbol":symbol,"asset_class":asset_class,"source":source,
        "created_at":now_iso(),"status":"candidate",
        "validation_status":report["status"],
        "research_only":True,"execution_enabled":False,
        "strategy":"R2_INTELLIGENCE_LOGISTIC_V1",
        "model":model,"training_job_id":job["_id"],
        "trained_feature_names":list(FEATURE_NAMES),
        "intelligence_evidence_asof":True,
        "production_inference_supported":False,
        **report,
    }
    await db.kaos_r2_research_models.insert_one(document)
    await db.kaos_r2_research_events.insert_one({
        "model_id":document["id"],"actor_id":job["owner_id"],
        "event":"intelligence_candidate_trained",
        "created_at":now_iso(),"training_job_id":job["_id"],
        "validation_status":document["validation_status"],
    })
    return {"status":"trained","model_id":document["id"],
            "validation_status":document["validation_status"],
            "source_categories":document["source_categories_in_training"],
            "coverage":coverage,"test":document.get("test"),
            "promotion_blockers":document.get("promotion_blockers",[])}


async def train_one_market(job, market):
    symbol=market["symbol"]
    asset_class=market["asset_class"]
    identity={"symbol":symbol,"asset_class":asset_class}
    try:
        rows,source=await read_archive(symbol,asset_class,60,limit=job["history_limit"])
        if len(rows)<300:
            return {**identity,"status":"insufficient_history",
                    "rows":len(rows),"source":source,
                    "training_sources":source_report(archive_status="missing",archive_rows=len(rows),source=source),
                    "reason":"Fewer than 300 closed validated R2 bars"}
        # Time-expensive fit is moved off the event loop.
        result=await asyncio.to_thread(train_from_candles,rows,60,job["horizon_bars"])
    except (ArchiveUnavailable,ValueError,RuntimeError,TimeoutError,OSError,ZeroDivisionError,OverflowError) as exc:
        return {**identity,"status":"source_error","rows":0,
                "training_sources":source_report(archive_status="missing"),
                "reason":type(exc).__name__}
    inventory=source_report(archive_status="ready",archive_rows=len(rows),source=source)
    if result["status"]=="insufficient_training_history":
        return {**identity,"status":"insufficient_history","rows":len(rows),
                "source":source,"training_sources":source_report(archive_status="available",archive_rows=len(rows),source=source),
                "reason":result["required"]}
    fingerprint=result["dataset_fingerprint"]
    model_filter={"owner_id":job["owner_id"],"symbol":symbol,
                  "asset_class":asset_class,"source":source,
                  "horizon_bars":job["horizon_bars"],
                  "dataset_fingerprint":fingerprint}
    existing=await db.kaos_r2_research_models.find_one(model_filter,{"id":1,"_id":0})
    if existing:
        output={**identity,"status":"reused","rows":len(rows),"source":source,
                "model_id":existing["id"],"training_sources":inventory}
    else:
        trained=result.pop("model")
        document={
            "id":new_id("r2model"),"owner_id":job["owner_id"],
            "symbol":symbol,"asset_class":asset_class,"source":source,
            "created_at":now_iso(),"status":"candidate",
            "validation_status":result["status"],
            "research_only":True,"execution_enabled":False,
            "strategy":"R2_OHLC_LOGISTIC_V1","model":trained,
            "training_job_id":job["_id"],"feature_sources":inventory,
            "training_features":list(TRAINED_FEATURES),
            "trained_on_news_social_insider_or_options":False,
            **result,
        }
        await db.kaos_r2_research_models.insert_one(document)
        await db.kaos_r2_research_events.insert_one({
            "model_id":document["id"],"actor_id":job["owner_id"],
            "event":"bulk_trained_candidate","created_at":now_iso(),
            "validation_status":document["validation_status"],
            "training_job_id":job["_id"],
        })
        output={**identity,"status":"trained","rows":len(rows),
                "source":source,"model_id":document["id"],
                "validation_status":document["validation_status"],
                "test":document.get("test"),
                "promotion_blockers":document.get("promotion_blockers",[]),
                "training_sources":inventory}
    try:
        enriched=await try_enriched_intelligence(job,market,rows,source)
    except Exception as exc:
        enriched={"status":"source_unavailable","reason":type(exc).__name__}
    output["intelligence_model"]=enriched
    if enriched["status"] in ("trained","reused"):
        # Accurate per-market source manifest. Only categories with time-safe
        # historical observations used by the enriched model get "trained".
        mapping={"insider_trades":"insider",
                 "institutional_trades":"institutional",
                 "macro_events":"macro"}
        categories=set(enriched.get("source_categories",[]))
        for item in inventory:
            source_key=mapping.get(item["key"],item["key"])
            if source_key in categories:
                item["used_in_training"]=True
                item["status"]="trained_in_separate_intelligence_model"
                item["rows"]=enriched["coverage"]["source_counts"].get(source_key)
        output["training_sources"]=inventory
    return output

async def run_tick():
    if os.getenv("KAOS_R2_TRAIN_WORKER_ENABLED")!="1":
        return {"status":"disabled","reason":"Set KAOS_R2_TRAIN_WORKER_ENABLED=1 on the Python worker"}
    if not configured():
        return {"status":"disabled","reason":"Cloudflare R2 credentials unavailable"}
    owner_id=os.getenv("KAOS_CANDLE_OWNER_USER_ID","")
    if not owner_id:
        return {"status":"disabled","reason":"KAOS owner ID missing"}
    from pymongo import ReturnDocument
    now=datetime.now(timezone.utc)
    token=uuid4().hex
    job=await db[JOB_COLLECTION].find_one_and_update(
        {"owner_id":owner_id,"status":{"$in":["queued","running"]},
         "$or":[{"lease_until":{"$lte":now}},{"lease_until":{"$exists":False}}]},
        {"$set":{"status":"running","lease_until":now+timedelta(minutes=LEASE_MINUTES),
                 "worker_token":token,"updated_at":now_iso()}},
        sort=[("created_at",1)],return_document=ReturnDocument.AFTER)
    if not job:return {"status":"idle","processed":0}
    processed=[]
    try:
        start=job["next_index"]
        for index in range(start,min(start+MAX_MARKETS_PER_TICK,job["total"])):
            market=job["markets"][index]
            try:
                row=await train_one_market(job,market)
            except Exception as exc:
                # Keep the job progressing without leaking source tokens or data.
                row={"symbol":market["symbol"],"asset_class":market["asset_class"],
                     "status":"failed","reason":type(exc).__name__,
                     "training_sources":source_report(archive_status="missing")}
            processed.append(row)
            count={"trained":0,"reused":0,"not_validated":0,"failed":0}
            if row["status"]=="trained":
                count["trained"]=1
                if row.get("validation_status")!="validated_research_candidate":
                    count["not_validated"]=1
            elif row["status"]=="reused":
                count["reused"]=1
            else: count["failed"]=1
            # Store progress only if this worker still owns the lease.
            update=await db[JOB_COLLECTION].update_one(
                {"_id":job["_id"],"worker_token":token,"next_index":index},
                {"$push":{"results":row},
                 "$inc":{"next_index":1,"completed":1,**count},
                 "$set":{"updated_at":now_iso(),
                         "lease_until":datetime.now(timezone.utc)+timedelta(minutes=LEASE_MINUTES)}})
            if update.modified_count!=1:
                raise RuntimeError("Training lease lost; safe abort")
        finished=start+len(processed)>=job["total"]
        await db[JOB_COLLECTION].update_one(
            {"_id":job["_id"],"worker_token":token},
            {"$set":{"status":"completed" if finished else "queued",
                     "updated_at":now_iso(),
                     "lease_until":datetime.fromtimestamp(0,timezone.utc),
                     "worker_token":None}})
        return {"status":"completed" if finished else "checkpointed",
                "job_id":job["_id"],"processed":len(processed),
                "total":job["total"]}
    except Exception:
        await db[JOB_COLLECTION].update_one(
            {"_id":job["_id"],"worker_token":token},
            {"$set":{"status":"queued","lease_until":datetime.fromtimestamp(0,timezone.utc),
                     "worker_token":None,"updated_at":now_iso()}})
        raise

if __name__=="__main__":
    print(asyncio.run(run_tick()))
