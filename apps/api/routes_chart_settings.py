"""Per-member chart configuration; authoritative slot checks at authenticated API boundary.

Chart settings do not enable order execution and cannot elevate a broker's trading permissions.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Literal
from auth import get_current_user
from db import db
from services_trading import get_entitlements

router = APIRouter(prefix="/api/v1/trading/charts", tags=["trading-charts"])
BROKERS = {"kaos_paper", "coinbase", "alpaca", "oanda"}
DEFAULTS = [
    {"broker": "kaos_paper", "symbol": "BTC-USD", "seconds": 60},
    {"broker": "kaos_paper", "symbol": "ETH-USD", "seconds": 60},
    {"broker": "kaos_paper", "symbol": "SOL-USD", "seconds": 60},
    {"broker": "kaos_paper", "symbol": "BTC-USD", "seconds": 300},
]

class ChartConfig(BaseModel):
    broker: Literal["kaos_paper", "coinbase", "alpaca", "oanda"] = "kaos_paper"
    symbol: str = Field(min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_:/-]+$")
    seconds: Literal[60, 300, 900] = 60

async def _limit(user):
    ent = await get_entitlements(user)
    return max(1, min(4, int(ent.get("chartLimit") or 1)))

async def _guard(user, slot):
    limit = await _limit(user)
    if isinstance(slot, bool) or slot < 0 or slot >= limit:
        raise HTTPException(403, f"Chart slot unavailable for your membership (limit {limit})")
    return limit

@router.get("")
async def list_charts(user: dict = Depends(get_current_user)):
    limit = await _limit(user)
    rows = await db.member_chart_settings.find({"user_id": user["id"]}, {"_id": 0}).to_list(4)
    saved = {r["slot"]: r for r in rows if isinstance(r.get("slot"), int) and 0 <= r["slot"] < limit}
    return {"chartLimit": limit, "charts": [
        {"slot": i, **(saved[i]["config"] if i in saved else DEFAULTS[i])}
        for i in range(limit)], "order_submission_enabled": False}

@router.put("/{slot}")
async def save_chart(slot: int, config: ChartConfig, user: dict = Depends(get_current_user)):
    limit = await _guard(user, slot)
    normalized = config.model_dump()
    normalized["symbol"] = normalized["symbol"].upper()
    await db.member_chart_settings.update_one(
        {"user_id": user["id"], "slot": slot},
        {"$set": {"user_id": user["id"], "slot": slot, "config": normalized}},
        upsert=True)
    return {"slot": slot, **normalized, "chartLimit": limit, "order_submission_enabled": False}
