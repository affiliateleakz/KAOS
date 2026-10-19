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
