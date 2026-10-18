"""KAOS AI: inference boundary, model registry/versioning/deployment, Collective Learning ingestion.

The inference endpoint is a real, authenticated production BOUNDARY. When an admin trains and
deploys a model, `/api/v1/ai/predict` runs REAL server-side inference over the native KAOS AI
tree bundle (learning/reporting only — no execution authority). Until a bundle is deployed it
returns a clearly-flagged simulated placeholder; it is never advertised as production-trained.
"""
import time
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Depends, Request
from db import db, new_id, now_iso, clean
from auth import get_current_user, require_role
from services import compute_license, audit_log
from services_trading import get_entitlements, kaos_ai_predict

v1ai = APIRouter(prefix="/api/v1/ai", tags=["ai-v1"])
mai = APIRouter(prefix="/api/ai", tags=["ai-member"])
aai = APIRouter(prefix="/api/admin/ai", tags=["ai-admin"])
admin_dep = require_role("admin")

FEATURE_SCHEMA = ["asset", "platform", "timeframe"]  # minimum required feature keys


async def _active_model():
    m = await db.ai_models.find_one({"status": "deployed"}, {"_id": 0}, sort=[("createdAt", -1)])
    return m or {"version": "kaos-ai-0.1.0-sim", "id": "sim", "status": "deployed", "simulated": True}


class PredictReq(BaseModel):
    asset: str
    platform: str = "pocket_option"
    timeframe: str = "5s"
    features: dict = {}
    featureVector: Optional[list] = None
    candles: Optional[list] = None


@v1ai.post("/predict")
async def predict(req: PredictReq, request: Request, user: dict = Depends(get_current_user)):
    did = request.headers.get("X-Device-Id")
    device = await db.devices.find_one({"installId": did, "userId": user["id"]}) if did else None
    lic = await compute_license(user, device)
    if not lic["authorized"]:
        raise HTTPException(status_code=403, detail={"error": "not_authorized"})
    missing = [k for k in FEATURE_SCHEMA if not getattr(req, k, None)]
    if missing:
        raise HTTPException(status_code=422, detail=f"Missing feature keys: {missing}")
    t0 = time.perf_counter()
    model = await _active_model()
    ctx = {"bucket": req.features.get("bucket", ""), "featureVector": req.featureVector,
           "x": req.featureVector, "features": req.featureVector, "candles": req.candles}
    out = await kaos_ai_predict(req.asset, req.platform, ctx)
    latency = round((time.perf_counter() - t0) * 1000, 2)
    simulated = bool(out.get("simulated"))
    rec = {"id": new_id("pred"), "userId": user["id"], "asset": req.asset, "platform": req.platform,
           "timeframe": req.timeframe, "prediction": out.get("direction"), "confidence": out.get("confidence"),
           "model_id": model.get("id"), "model_version": out.get("modelVersion") or model.get("version"),
           "latencyMs": latency, "modelKind": out.get("modelKind"), "probUp": out.get("probUp"),
           "productionTrained": not simulated, "simulated": simulated, "timestamp": now_iso(), "outcome": None}
    await db.ai_predictions.insert_one(dict(rec))
    note = ("Live KAOS AI inference (native tree bundle). Learning/reporting only — no execution authority."
            if not simulated else
            "SIMULATED — no deployed model bundle or feature vector supplied. Real model runs once trained & deployed.")
    return {"prediction": out.get("direction"), "confidence": out.get("confidence"),
            "model_id": model.get("id"), "model_version": rec["model_version"],
            "prob_up": out.get("probUp"), "model_kind": out.get("modelKind"),
            "latency_ms": latency, "timestamp": rec["timestamp"], "source": "AI",
            "authority": "LEARNING_ONLY", "simulated": simulated, "note": note}



class BrainReq(BaseModel):
    mode: str = "shadow"
    schema: str = "KAOS_BRAIN_V1"
    horizons: list = [5, 10, 15, 30]
    snapshot: dict = {}


@v1ai.post("/brain")
async def openai_brain(
    req: BrainReq,
    request: Request,
    user: dict = Depends(get_current_user)
):
    """KAOS OpenAI Brain — authenticated, paid-member, learning-only inference."""

    import os
    import json
    import asyncio
    import requests

    # Use the same KAOS device/license authorization as /predict.
    did = request.headers.get("X-Device-Id")
    device = (
        await db.devices.find_one({
            "installId": did,
            "userId": user["id"]
        })
        if did else None
    )

    lic = await compute_license(user, device)

    if not lic.get("authorized"):
        raise HTTPException(
            status_code=403,
            detail={"error": "not_authorized"}
        )

    # Require ACTIVE paid membership for OpenAI server resources.
    if str(user.get("membership_status", "")).upper() != "ACTIVE":
        raise HTTPException(
            status_code=403,
            detail="Active paid KAOS membership required"
        )

    api_key = (os.environ.get("OPENAI_API_KEY") or "").strip()

    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="OpenAI Brain is not configured on the KAOS server"
        )

    snapshot = req.snapshot or {}

    try:
        snapshot_json = json.dumps(
            snapshot,
            separators=(",", ":"),
            default=str
        )
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid market snapshot"
        )

    if len(snapshot_json) > 50000:
        raise HTTPException(
            status_code=413,
            detail="Market snapshot too large"
        )

    model = os.environ.get(
        "KAOS_OPENAI_MODEL",
        "gpt-5.6"
    )

    output_schema = {
        "type": "object",
        "properties": {
            "direction": {
                "type": "string",
                "enum": ["BUY", "SELL", "HOLD"]
            },
            "confidence": {
                "type": "number",
                "minimum": 0,
                "maximum": 100
            },
            "expirySec": {
                "anyOf": [
                    {
                        "type": "integer",
                        "enum": [5, 10, 15, 30]
                    },
                    {
                        "type": "null"
                    }
                ]
            },
            "regime": {
                "type": "string"
            },
            "setupType": {
                "type": "string"
            }
        },
        "required": [
            "direction",
            "confidence",
            "expirySec",
            "regime",
            "setupType"
        ],
        "additionalProperties": False
    }

    payload = {
        "model": model,

        "instructions": (
            "You are KAOS Brain, a shadow-mode market-state "
            "classifier for short-duration trading research. "
            "Analyze ONLY the supplied structured market snapshot. "
            "Return BUY, SELL, or HOLD. "
            "Prefer HOLD when evidence conflicts or is insufficient. "
            "Do not claim certainty or guaranteed profitability."
        ),

        "input": snapshot_json,

        "text": {
            "format": {
                "type": "json_schema",
                "name": "kaos_brain_result",
                "strict": True,
                "schema": output_schema
            }
        }
    }

    def call_openai():
        return requests.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": "Bearer " + api_key,
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=30
        )

    try:
        response = await asyncio.to_thread(call_openai)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="Could not reach OpenAI"
        ) from exc

    if response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail={
                "error": "openai_upstream_error",
                "status": response.status_code
            }
        )

    raw = response.json()

    text = ""

    for item in raw.get("output") or []:
        if item.get("type") != "message":
            continue

        for part in item.get("content") or []:
            if part.get("type") == "output_text":
                text = part.get("text") or ""
                break

        if text:
            break

    if not text:
        raise HTTPException(
            status_code=502,
            detail="OpenAI returned no structured result"
        )

    try:
        result = json.loads(text)
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Invalid OpenAI structured response"
        )

    result.update({
        "model": model,
        "requestId": raw.get("id"),
        "shadowOnly": True,
        "authority": "LEARNING_ONLY"
    })

    # Record prediction for later KAOS performance analysis.
    try:
        await db.ai_predictions.insert_one({
            "id": new_id("oai"),
            "userId": user["id"],
            "source": "OPENAI_BRAIN",
            "asset": snapshot.get("asset"),
            "prediction": result.get("direction"),
            "confidence": result.get("confidence"),
            "expirySec": result.get("expirySec"),
            "regime": result.get("regime"),
            "setupType": result.get("setupType"),
            "model_version": model,
            "requestId": raw.get("id"),
            "timestamp": now_iso(),
            "outcome": None,
            "authority": "LEARNING_ONLY"
        })
    except Exception:
        # Prediction logging must never break inference.
        pass

    return result


class LearningSample(BaseModel):
    sampleId: str
    sampleType: str            # REAL | PAPER
    platform: str
    asset: str
    assetClass: Optional[str] = None
    timeframe: str
    expiration: str
    strategy: Optional[str] = None
    strategyVersion: Optional[str] = None
    direction: Optional[str] = None
    aiPrediction: Optional[str] = None
    aiConfidence: Optional[float] = None
    aiModelVersion: Optional[str] = None
    entryPrice: Optional[float] = None
    settlementPrice: Optional[float] = None
    outcome: Optional[str] = None   # WIN | LOSS | TIE
    features: dict = {}
    botVersion: Optional[str] = None
    timestamp: Optional[str] = None


@v1ai.post("/learning-samples")
async def learning_samples(s: LearningSample, user: dict = Depends(get_current_user)):
    if not user.get("collective_learning_consent"):
        raise HTTPException(status_code=403, detail="Collective Learning consent required")
    if s.sampleType not in ("REAL", "PAPER"):
        raise HTTPException(status_code=400, detail="Invalid sampleType")
    if await db.learning_samples.find_one({"sampleId": s.sampleId}):
        return {"sampleId": s.sampleId, "duplicate": True}
    # anonymized: no name/email/credentials/balance. Stable anonymous learning id per user.
    anon = user.get("learning_id")
    if not anon:
        anon = new_id("lrn")
        await db.users.update_one({"id": user["id"]}, {"$set": {"learning_id": anon}})
    doc = s.model_dump()
    doc.update({"id": new_id("sample"), "learningId": anon, "status": "ingested",
                "createdAt": now_iso(), "timestamp": s.timestamp or now_iso()})
    await db.learning_samples.insert_one(dict(doc))
    return {"sampleId": s.sampleId, "duplicate": False, "learningId": anon}


@v1ai.get("/model")
async def model_info():
    return await _active_model()


@v1ai.get("/status")
async def ai_status():
    total = await db.learning_samples.count_documents({})
    deployed_bundle = await db.ai_models.find_one({"status": "deployed", "bundle": {"$ne": None}}, {"_id": 0})
    return {"activeModel": await _active_model(), "learningSamples": total,
            "productionTrained": bool(deployed_bundle)}


@mai.get("/overview")
async def ai_overview(user: dict = Depends(get_current_user)):
    real = await db.learning_samples.count_documents({"learningId": user.get("learning_id"), "sampleType": "REAL"}) if user.get("learning_id") else 0
    paper = await db.learning_samples.count_documents({"learningId": user.get("learning_id"), "sampleType": "PAPER"}) if user.get("learning_id") else 0
    preds = await db.ai_predictions.find({"userId": user["id"]}, {"_id": 0}).sort("timestamp", -1).to_list(20)
    return {"activeModel": await _active_model(), "consent": bool(user.get("collective_learning_consent")),
            "realSamples": real, "paperSamples": paper, "recentPredictions": preds,
            "entitlements": await get_entitlements(user)}


# ---- admin AI control center ----
@aai.get("/models")
async def models(admin: dict = Depends(admin_dep)):
    return await db.ai_models.find({}, {"_id": 0}).sort("createdAt", -1).to_list(200)


class DeployReq(BaseModel):
    modelId: str
    override: bool = False


@aai.post("/models/deploy")
async def deploy(req: DeployReq, admin: dict = Depends(admin_dep)):
    candidate = await db.ai_models.find_one({"id": req.modelId})
    if not candidate:
        raise HTTPException(status_code=404, detail="Model not found")
    current = await db.ai_models.find_one({"status": "deployed"})
    cand_acc = (candidate.get("report") or {}).get("holdoutAccuracy")
    live_acc = (current.get("report") or {}).get("holdoutAccuracy") if current else None
    if (not req.override and current and current["id"] != req.modelId
            and cand_acc is not None and live_acc is not None and cand_acc < live_acc):
        raise HTTPException(status_code=409, detail={
            "error": "below_live", "candidateAccuracy": cand_acc, "liveAccuracy": live_acc,
            "message": (f"Candidate holdout {cand_acc*100:.1f}% is below the live model "
                        f"{live_acc*100:.1f}%. Deploy with override to force promotion.")})
    await db.ai_models.update_many({"status": "deployed"}, {"$set": {"status": "candidate"}})
    await db.ai_models.update_one({"id": req.modelId}, {"$set": {"status": "deployed", "deployedAt": now_iso()}})
    await db.model_deployments.insert_one({"id": new_id("dep"), "modelId": req.modelId, "action": "deploy",
                                           "overrode": bool(req.override), "actorId": admin["id"], "createdAt": now_iso()})
    await audit_log(admin, "ai_deploy", "ai_model", req.modelId, {"override": bool(req.override)})
    return {"ok": True, "overrode": bool(req.override)}


@aai.post("/models/rollback")
async def rollback(req: DeployReq, admin: dict = Depends(admin_dep)):
    await db.ai_models.update_one({"id": req.modelId}, {"$set": {"status": "retired"}})
    await db.model_deployments.insert_one({"id": new_id("dep"), "modelId": req.modelId, "action": "rollback",
                                           "actorId": admin["id"], "createdAt": now_iso()})
    await audit_log(admin, "ai_rollback", "ai_model", req.modelId)
    return {"ok": True}


@aai.get("/learning")
async def learning_stats(admin: dict = Depends(admin_dep)):
    total = await db.learning_samples.count_documents({})
    real = await db.learning_samples.count_documents({"sampleType": "REAL"})
    paper = await db.learning_samples.count_documents({"sampleType": "PAPER"})
    consented = await db.users.count_documents({"collective_learning_consent": True})
    return {"totalSamples": total, "realSamples": real, "paperSamples": paper, "consentedUsers": consented,
            "datasets": await db.learning_dataset_versions.find({}, {"_id": 0}).to_list(50),
            "trainingRuns": await db.training_runs.find({}, {"_id": 0}).sort("createdAt", -1).to_list(50)}


class TrainingRunReq(BaseModel):
    modelId: str
    featureSchemaVersion: str
    datasetVersion: str
    trainRange: str
    validationRange: str
    oosRange: str
    metrics: dict = {}


@aai.post("/training-runs")
async def register_training_run(req: TrainingRunReq, admin: dict = Depends(admin_dep)):
    """Registers a training-run record. Raw samples NEVER auto-modify the production model —
    a run must pass chronological + out-of-sample validation and explicit admin deploy."""
    doc = {"id": new_id("run"), **req.model_dump(), "status": "candidate",
           "actorId": admin["id"], "createdAt": now_iso()}
    await db.training_runs.insert_one(dict(doc))
    await audit_log(admin, "register_training_run", "training_run", doc["id"])
    return clean(doc)



def _ts_ms(v) -> int:
    """Best-effort convert an ISO/epoch timestamp to epoch ms."""
    if v is None:
        return 0
    if isinstance(v, (int, float)):
        return int(v if v > 1e12 else v * 1000)
    try:
        return int(datetime.fromisoformat(str(v).replace("Z", "+00:00")).timestamp() * 1000)
    except Exception:
        return 0


def _derive_label(sample: dict, feats: dict):
    """Label = 1 if price went UP over the horizon, else 0. TIE -> None (skipped)."""
    if "label" in feats and feats["label"] is not None:
        try:
            return 1 if float(feats["label"]) >= 0.5 else 0
        except Exception:
            return None
    ep, sp = sample.get("entryPrice"), sample.get("settlementPrice")
    if isinstance(ep, (int, float)) and isinstance(sp, (int, float)):
        if sp == ep:
            return None
        return 1 if sp > ep else 0
    outcome, direction = sample.get("outcome"), sample.get("direction")
    if outcome in ("WIN", "LOSS") and direction in ("BUY", "SELL"):
        went_up = (direction == "BUY") == (outcome == "WIN")
        return 1 if went_up else 0
    return None


@aai.post("/train")
async def train_ai_model(admin: dict = Depends(admin_dep)):
    """Train a REAL KAOS AI model (native XGBoost/LightGBM tree bundle) over collected
    Collective Learning samples that carry a 104-feature vector (features.x) and an outcome.

    The resulting model is registered as a CANDIDATE only — it never auto-deploys. An admin must
    explicitly deploy it. AI has no execution authority over the deterministic KAOS Strategy.
    """
    import asyncio
    import kaos_ai_trainer
    samples = await db.learning_samples.find({}, {"_id": 0}).to_list(5000)
    training, skipped = [], 0
    for s in samples:
        feats = s.get("features") or {}
        x = feats.get("x")
        if not isinstance(x, list) or len(x) not in (88, 104):
            skipped += 1
            continue
        label = _derive_label(s, feats)
        if label is None:
            skipped += 1
            continue
        training.append({"x": x, "label": label, "t": _ts_ms(s.get("timestamp") or s.get("createdAt")),
                         "asset": s.get("asset", "UNKNOWN")})
    if len(training) < 12:
        raise HTTPException(status_code=400,
                            detail=f"Need >=12 labeled feature-vector samples to train (usable={len(training)}, skipped={skipped}).")
    msg = {"type": "train_xgboost", "samples": training, "targetHorizonMs": 30000,
           "now": int(time.time() * 1000)}
    result = await asyncio.to_thread(kaos_ai_trainer.main, msg)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail={"error": "training_failed", **result})
    bundle, report = result["model"], result["report"]
    version = f"kaos-ai-{report.get('featureCount', 104)}f-{int(time.time())}"
    doc = {"id": new_id("model"), "version": version, "status": "candidate", "bundle": bundle,
           "report": report, "trainedSamples": bundle.get("trainedSamples"),
           "totalSamples": bundle.get("totalSamples"), "productionTrained": True,
           "simulated": False, "createdAt": now_iso()}
    await db.ai_models.insert_one(dict(doc))
    await db.training_runs.insert_one({"id": new_id("run"), "modelId": doc["id"], "status": "candidate",
                                       "featureSchemaVersion": report.get("trainerSchema"),
                                       "usableSamples": len(training), "skippedSamples": skipped,
                                       "metrics": {"holdoutAccuracy": report.get("holdoutAccuracy"),
                                                   "trainAccuracy": report.get("trainAccuracy")},
                                       "actorId": admin["id"], "createdAt": now_iso()})
    await audit_log(admin, "train_ai_model", "ai_model", doc["id"], {"version": version})
    return {"ok": True, "modelId": doc["id"], "version": version, "usableSamples": len(training),
            "skippedSamples": skipped, "report": report}
