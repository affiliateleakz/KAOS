"""Per-member broker selection for KAOS UI and future execution routing.

Selection is not connection verification or authorization to submit orders.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from auth import get_current_user
from db import db
from broker_adapters import REGISTRY

router=APIRouter(prefix="/api/v1/broker-selection",tags=["broker-selection"])

class Selection(BaseModel):
    broker: str

@router.get("")
async def get_selection(user:dict=Depends(get_current_user)):
    record=await db.member_broker_selections.find_one({"user_id":user["id"]},{"_id":0})
    broker=record.get("broker") if record else None
    return {"broker":broker if broker in REGISTRY else None,"live_order_authorized":False,
            "note":"Selecting a broker does not connect an account or enable trading."}

@router.put("")
async def set_selection(req:Selection,user:dict=Depends(get_current_user)):
    broker=req.broker
    if broker not in REGISTRY:
        raise HTTPException(422,"Unknown broker; select one from the KAOS broker catalog")
    # The member can choose any catalog broker, including a planned provider.
    # It is never mistaken for a working account or execution approval.
    await db.member_broker_selections.update_one({"user_id":user["id"]},
        {"$set":{"user_id":user["id"],"broker":broker}},upsert=True)
    return {"broker":broker,"status":REGISTRY[broker].status,
            "live_order_authorized":False,
            "note":"Preference saved. Account connection and broker-specific execution approval are separate."}
