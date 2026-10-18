"""Account-specific broker preference, not an execution authorization."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from auth import get_current_user
from db import db

router = APIRouter(prefix="/api/v1/broker-selection", tags=["broker-selection"])
# Catalog choices do not imply implemented connectivity or permission to trade.
BROKERS = ("coinbase", "pocketoption", "alpaca", "oanda", "kraken", "ibkr", "tradier", "tastytrade", "mt5")

class Preference(BaseModel):
    broker: str

@router.get("")
async def get_preference(user: dict = Depends(get_current_user)):
    row = await db.member_broker_selections.find_one({"user_id": user["id"]}, {"_id": 0, "broker": 1})
    return {"broker": row["broker"] if row and row.get("broker") in BROKERS else None,
            "live_order_authorized": False}

@router.put("")
async def save_preference(request: Preference, user: dict = Depends(get_current_user)):
    if request.broker not in BROKERS:
        raise HTTPException(status_code=422, detail="Unsupported broker selection")
    await db.member_broker_selections.update_one({"user_id": user["id"]},
        {"$set": {"user_id": user["id"], "broker": request.broker}}, upsert=True)
    return {"broker": request.broker, "live_order_authorized": False,
            "message": "Preference saved; verify connection and independent order authorization before trading"}
