"""KAOS read-only Alpaca paper account bridge.

No live API hostname, no paper order submission, and no AI trade authority.
This is the verified account/positions/order sync foundation.
"""
from fastapi import APIRouter,Depends,HTTPException,Query
from auth import get_current_user
from db import db
from broker_vault import vault
from alpaca_paper_client import (
    AlpacaPaperUnavailable,paper_account,paper_positions,paper_orders
)
router=APIRouter(prefix="/api/v1/alpaca-paper",tags=["alpaca-paper"])

async def credentials(user):
    if user.get("account_status","active")!="active" or user.get("extension_access_revoked"):
        raise HTTPException(403,"Account disabled")
    doc=await db.broker_connections.find_one(
        {"user_id":user["id"],"broker":"alpaca_paper","verified":True,
         "paper_only":True})
    if not doc:
        raise HTTPException(403,"Verified Alpaca PAPER connection required")
    crypt=vault()
    try:
        return (crypt.decrypt(doc["key_name_enc"].encode()).decode(),
                crypt.decrypt(doc["private_key_enc"].encode()).decode())
    except Exception as exc:
        raise HTTPException(503,"Alpaca paper credentials cannot be decrypted") from exc

@router.get("/snapshot")
async def snapshot(user:dict=Depends(get_current_user)):
    key,secret=await credentials(user)
    try:
        account=await paper_account(key,secret)
        positions=await paper_positions(key,secret)
        orders=await paper_orders(key,secret)
    except AlpacaPaperUnavailable as exc:
        raise HTTPException(503,str(exc)) from exc
    return {
        "broker":"alpaca_paper","paper_only":True,
        "account":account,"positions":positions,"orders":orders,
        "order_submission_enabled":False,
        "ai_execution_enabled":False,
        "note":"Alpaca paper portfolio is simulated; KAOS AI order submission not connected."
    }


@router.get("/candles/{symbol}")
async def paper_stock_chart(
    symbol:str,seconds:int=Query(default=60),
    user:dict=Depends(get_current_user)
):
    """Authenticated read-only Alpaca stock chart. No order or AI authority."""
    from alpaca_paper_quotes import stock_candles,MarketUnavailable
    key,secret=await credentials(user)
    try:
        return await stock_candles(key,secret,symbol.strip().upper(),seconds)
    except MarketUnavailable as exc:
        raise HTTPException(503,str(exc)) from exc
