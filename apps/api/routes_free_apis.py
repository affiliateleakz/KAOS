"""Admin-owned free-data API registry. Storage only; no unreviewed outbound requests.
Keys encrypted at rest using the existing server vault, never returned to clients.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from auth import require_role
from db import db
from broker_vault import vault

router=APIRouter(prefix="/api/admin/data-apis",tags=["admin-data-apis"])
admin_dep=require_role("admin")

# Only no-cost public endpoints and documented free-key options. An API's free
# plan does NOT establish commercial redisplay rights; never auto-enable feeds.
SOURCES=(
 {"id":"coinbase_public","name":"Coinbase Exchange public candles","category":"crypto","access":"free_public","key_required":False,"usable":True,"note":"Existing public candle feed; subject to terms, rate limits and outages."},
 {"id":"bluesky_public","name":"Bluesky public AppView","category":"social","access":"free_public","key_required":False,"usable":True,"note":"Existing bounded Bluesky collectors; not full-platform sentiment."},
 {"id":"sec_edgar","name":"SEC EDGAR public disclosures","category":"filings","access":"free_public","key_required":False,"usable":False,"note":"Public endpoints; require declared user agent, rate limits and licensed data review."},
 {"id":"hyperliquid_public","name":"Hyperliquid public info","category":"crypto","access":"free_public","key_required":False,"usable":False,"note":"Independent on-chain research; NOT Invo user data."},
 {"id":"alpha_vantage_free","name":"Alpha Vantage free tier","category":"stock","access":"free_key","key_required":True,"usable":False,"note":"25 requests/day on free plan; commercial redistribution and market-data licensing require approval."},
 {"id":"fred_free","name":"FRED public API","category":"macro","access":"free_key","key_required":True,"usable":False,"note":"Free key; individual series may carry third-party copyrights and additional display terms."},
)
BY_ID={s["id"]:s for s in SOURCES}

class KeyInput(BaseModel):
    api_key: str=Field(min_length=8,max_length=1024)

@router.get("")
async def catalog(admin:dict=Depends(admin_dep)):
    docs=await db.admin_free_api_credentials.find({},{"_id":0,"provider":1}).to_list(25)
    configured={r["provider"] for r in docs}
    return {"sources":[{**s,"key_saved":s["id"] in configured if s["key_required"] else False,
                       "connected":bool(s["usable"] and not s["key_required"]),
                       "commercial_approval":False} for s in SOURCES],
            "automatic_paid_api_calls":False}

@router.put("/{provider}")
async def save_key(provider:str,body:KeyInput,admin:dict=Depends(admin_dep)):
    source=BY_ID.get(provider)
    if not source or not source["key_required"] or source["access"]!="free_key":
        raise HTTPException(422,"Provider does not accept API keys in the free catalog")
    encrypted=vault().encrypt(body.api_key.encode()).decode()
    await db.admin_free_api_credentials.update_one({"provider":provider},
        {"$set":{"provider":provider,"key_enc":encrypted}},upsert=True)
    return {"provider":provider,"key_saved":True,"connected":False,"commercial_approval":False}

@router.delete("/{provider}")
async def delete_key(provider:str,admin:dict=Depends(admin_dep)):
    source=BY_ID.get(provider)
    if not source or not source["key_required"]:
        raise HTTPException(404,"Unknown keyed provider")
    await db.admin_free_api_credentials.delete_one({"provider":provider})
    return {"provider":provider,"key_saved":False}
