"""Server-only verification of predictions using trusted stored market observations."""
from fastapi import APIRouter,Depends,Header,HTTPException
from pydantic import BaseModel,Field
from secrets import compare_digest
from auth import require_role
from db import db
from kaos_ai_outcome_verifier import verify
import os

router=APIRouter(prefix="/api/admin/ai",tags=["ai-outcomes"])
admin_dep=require_role("admin")

class SettleRequest(BaseModel):
    prediction_id:str=Field(min_length=3,max_length=150)
    horizon_seconds:int=Field(ge=5,le=3600)

@router.post("/settle-verified")
async def settle_verified(req:SettleRequest,admin=Depends(admin_dep)):
    """Never accepts member-submitted prices or user-asserted WIN/LOSS labels."""
    pred=await db.ai_predictions.find_one({"id":req.prediction_id})
    if not pred:raise HTTPException(404,"Prediction not found")
    if pred.get("outcomeVerified"):raise HTTPException(409,"Already settled")
    if pred.get("simulated") or not pred.get("productionTrained"):
        raise HTTPException(422,"Not a trained real prediction")
    if pred.get("horizon_seconds") != req.horizon_seconds or not pred.get("source"):
        raise HTTPException(422,"Prediction horizon or source provenance missing or mismatched")
    quotes=await db.kaos_ai_quote_observations.find(
        {"prediction_id":req.prediction_id,"asset":pred.get("asset"),"source":pred["source"]},{"_id":0}).sort("observed_at",1).limit(100).to_list(length=100)
    if len(quotes)<2:raise HTTPException(409,"Independent entry and expiry observations not available")
    result=None
    for first in quotes:
        for last in quotes:
            try:result=verify(pred,first,last,req.horizon_seconds);break
            except (ValueError,KeyError,TypeError):continue
        if result:break
    if not result:raise HTTPException(409,"No matching verified same-source entry/expiry quotes")
    update=await db.ai_predictions.update_one({"id":req.prediction_id,"outcomeVerified":{"$ne":True}},
      {"$set":result})
    if update.modified_count!=1:raise HTTPException(409,"Already settled")
    return {"prediction_id":req.prediction_id,**result,"execution_enabled":False}

class CollectorObservation(BaseModel):
    prediction_id:str=Field(min_length=3,max_length=150)
    asset:str=Field(min_length=2,max_length=60)
    source:str=Field(min_length=3,max_length=90)
    observed_at:str=Field(min_length=20,max_length=40)
    price:str=Field(min_length=1,max_length=40)

@router.post("/quote-observations")
async def record_observations(items:list[CollectorObservation],x_kaos_collector_key:str|None=Header(None)):
    key=os.environ.get("KAOS_COLLECTOR_KEY","")
    if not key or not x_kaos_collector_key or not compare_digest(key,x_kaos_collector_key):
        raise HTTPException(403,"Server collector authentication required")
    if not 1<=len(items)<=100:raise HTTPException(422,"Batch must contain 1-100 observations")
    # These fields are accepted only from the trusted server collector, not member browsers.
    for item in items:
        from decimal import Decimal
        from kaos_ai_outcome_verifier import timestamp
        try:
            price=Decimal(item.price)
            ts=timestamp(item.observed_at)
            if not price.is_finite() or price<=0 or ts<=0:raise ValueError()
        except (ValueError,ArithmeticError,TypeError) as exc:
            raise HTTPException(422,"Invalid market observation") from exc
    for item in items:
        await db.kaos_ai_quote_observations.update_one(
          {"prediction_id":item.prediction_id,"asset":item.asset,"source":item.source,
           "observed_at":item.observed_at},{"$setOnInsert":item.model_dump()},upsert=True)
    return {"accepted":len(items),"verified_outcomes_created":0,"research_only":True}
