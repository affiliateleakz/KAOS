"""Read-only owner export for timestamped market intelligence training observations."""
from fastapi import APIRouter, Depends, Query
from auth import get_current_user
from db import db
from routes_owner_candles import require_owner

router = APIRouter(prefix="/api/v1/owner/intelligence", tags=["owner-research"])


@router.get("/export")
async def intelligence_export(
    asset: str = Query(pattern=r"^[A-Z0-9_.-]{2,32}$"),
    asset_class: str = Query(pattern="^(crypto|stock|forex)$"),
    limit: int = Query(1000, ge=1, le=5000),
    user: dict = Depends(get_current_user),
):
    require_owner(user)
    query = {"asset": asset, "asset_class": asset_class,
             "source": {"$in": ["news", "social"]}}
    docs = (await db.kaos_intelligence.find(query, {"_id": 0})
            .sort("observed_at", -1).limit(limit).to_list(length=limit))
    return {"asset": asset, "asset_class": asset_class, "observations": list(reversed(docs)),
            "research_only": True, "count_type": "collected_source_observations_not_global_mentions"}
