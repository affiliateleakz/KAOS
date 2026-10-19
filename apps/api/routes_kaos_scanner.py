"""Authenticated, research-only market opportunity scanner.

Input evidence must be supplied by trusted collectors in production. Client
submissions are never promoted to verified or executable status by this API.
"""
from datetime import datetime, timezone
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from auth import get_current_user
from kaos_opportunity_fusion import evaluate_opportunity
from services_trading import get_entitlements
from db import db
from kaos_opportunity import evaluate, SUPPORTED

router = APIRouter(prefix="/api/v1/kaos-ai", tags=["kaos-ai-scanner"])


class Evidence(BaseModel):
    source: Literal["chart", "indicators", "strategy", "news", "social", "financial_llm", "orderflow"]
    asset: str = Field(min_length=1, max_length=30)
    direction: Literal["BUY", "SELL"]
    timestamp: datetime
    confidence: float | None = Field(default=None, ge=0, le=1)


class ScanInput(BaseModel):
    broker: str = Field(min_length=1, max_length=30)
    assets: dict[str, list[Evidence]] = Field(min_length=1, max_length=30)


@router.post("/scan/preview")
async def scan_preview(req: ScanInput, user: dict = Depends(get_current_user)):
    """Untrusted user evidence: research preview only, never broker instructions.

    Source collectors and their cryptographic provenance are not wired yet.
    Enforce unverified input here regardless of any user-provided data.
    """
    if user.get("account_status", "active") in ("suspended", "banned"):
        raise HTTPException(status_code=403, detail="Account unavailable")
    if not user.get("id"):
        raise HTTPException(status_code=403, detail="Authenticated account required")
    if sum(len(rows) for rows in req.assets.values()) > 500:
        raise HTTPException(status_code=422, detail="Too many observations")
    results = []
    for asset, observations in req.assets.items():
        if not asset or len(asset) > 30:
            raise HTTPException(status_code=422, detail="Invalid asset")
        rows = [{**item.model_dump(), "verified": False, "simulated": False}
                for item in observations]
        result = evaluate_opportunity(asset, req.broker, rows)
        results.append(result)
    return {"mode": "UNTRUSTED_PREVIEW", "executable": False, "scanned": len(results),
            "opportunities": results}


@router.get("/scan/collected")
async def collected_opportunities(asset_class: str | None = None,
                                  limit: int = 30,
                                  user: dict = Depends(get_current_user)):
    """Show scored opportunities from KAOS's existing authenticated collector.

    Does not infer verified fills, execution permissions, or source authenticity
    merely because an observation exists in the research database.
    """
    if not (await get_entitlements(user)).get("scanners"):
        raise HTTPException(status_code=403, detail="Scanner entitlement required")
    if asset_class is not None and asset_class not in SUPPORTED:
        raise HTTPException(status_code=422, detail="Unsupported asset class")
    if not 1 <= limit <= 100:
        raise HTTPException(status_code=422, detail="Invalid limit")
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    query = {"observed_at": {"$gte": cutoff}}
    if asset_class:
        query["asset_class"] = asset_class
    rows = await db.kaos_intelligence.find(query, {"_id": 0}).sort(
        "observed_at", -1).limit(5000).to_list(length=5000)
    groups = {}
    for row in rows:
        if isinstance(row, dict) and row.get("asset") and row.get("asset_class"):
            groups.setdefault((row["asset"], row["asset_class"]), []).append(row)
    results = [dict(evaluate(asset, observations), asset_class=kind)
               for (asset, kind), observations in groups.items()]
    results.sort(key=lambda r: r.get("score", 0), reverse=True)
    return {"mode": "COLLECTOR_RESEARCH", "executable": False,
            "coverage": "ingested_sources_only", "scanned_observations": len(rows),
            "opportunities": results[:limit],
            "note": "Research rankings from stored collector observations; not verified executable signals or probabilities."}


@router.get("/models/status")
async def financial_models_status(user: dict = Depends(get_current_user)):
    """Expose actual local model provisioning without loading or downloading weights."""
    import os
    from pathlib import Path
    from kaos_financial_model_registry import catalog
    if not (await get_entitlements(user)).get("aiInsights"):
        raise HTTPException(status_code=403, detail="AI insights entitlement required")
    models = catalog()
    # Presence of a directory alone is not proof of working inference.
    path = os.getenv("KAOS_TRADING_HERO_MODEL_DIR", "").strip()
    staged = bool(path and Path(path).is_dir())
    for entry in models:
        if entry["id"] == "trading_hero":
            entry["status"] = "FILES_PRESENT_UNVERIFIED" if staged else "NOT_CONFIGURED"
            entry["weights_present"] = staged
            entry["inference_verified"] = False
    return {"models": models, "live_ai_trading_enabled": False,
            "note": "Model availability must be confirmed by a separate smoke test; files alone do not confirm inference."}
