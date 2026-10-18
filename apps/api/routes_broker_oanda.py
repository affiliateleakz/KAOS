"""OANDA v20 PRACTICE read-only broker connection.

Uses only api-fxpractice.oanda.com. No order submission and no production endpoint.
Never log or return member bearer tokens.
"""
from datetime import datetime, timezone
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from auth import get_current_user
from db import db
import broker_vault

router = APIRouter(prefix="/api/v1/broker-connections/oanda", tags=["brokers"])
PRACTICE_URL = "https://api-fxpractice.oanda.com"
TIMEOUT = 12.0

class ConnectRequest(BaseModel):
    account_id: str = Field(min_length=3, max_length=80, pattern=r"^[A-Za-z0-9-]+$")
    api_token: str = Field(min_length=12, max_length=1024)

async def oanda_get(path: str, token: str):
    # Explicit path allowlist prevents arbitrary outbound requests.
    if not (path.startswith("/v3/accounts/") and
            (path.endswith("/summary") or path.endswith("/openPositions") or
             path.endswith("/pendingOrders"))):
        raise HTTPException(400, "Unsupported OANDA endpoint")
    parts = path.split("/")
    if len(parts) != 5 or not parts[3] or not all(c.isalnum() or c == "-" for c in parts[3]):
        raise HTTPException(400, "Invalid OANDA account")
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=False) as client:
            res = await client.get(PRACTICE_URL + path, headers={
                "Authorization": "Bearer " + token, "Accept": "application/json"})
        if res.status_code in (401, 403):
            raise HTTPException(422, "OANDA practice credentials rejected")
        if res.status_code == 404:
            raise HTTPException(404, "OANDA practice account not found")
        if res.status_code != 200:
            raise HTTPException(502, "OANDA practice account data unavailable")
        return res.json()
    except HTTPException:
        raise
    except (httpx.HTTPError, ValueError):
        raise HTTPException(502, "OANDA practice API unavailable")

def _only(data, fields):
    return {k: data.get(k) for k in fields if k in data}

async def _credentials(user_id):
    row = await db.broker_connections.find_one(
        {"user_id": user_id, "broker": "oanda", "verified": True})
    if not row:
        raise HTTPException(404, "No OANDA practice account connected")
    try:
        v = broker_vault.vault()
        return v.decrypt(row["key_name_enc"].encode()).decode(), v.decrypt(row["private_key_enc"].encode()).decode()
    except Exception:
        raise HTTPException(503, "OANDA credentials unavailable; reconnect")

@router.put("")
async def connect(req: ConnectRequest, user: dict = Depends(get_current_user)):
    account_id, token = req.account_id.strip(), req.api_token.strip()
    v = broker_vault.vault()
    result = await oanda_get(f"/v3/accounts/{account_id}/summary", token)
    account = result.get("account") if isinstance(result, dict) else None
    if not isinstance(account, dict) or account.get("id") != account_id:
        raise HTTPException(502, "OANDA account verification failed")
    row = {"user_id": user["id"], "broker": "oanda", "verified": True,
           "key_name_enc": v.encrypt(account_id.encode()).decode(),
           "private_key_enc": v.encrypt(token.encode()).decode(),
           "key_hint": "…" + account_id[-4:], "environment": "practice",
           "permissions": {"can_view": True, "can_trade": False, "can_transfer": False},
           "connected_at": datetime.now(timezone.utc).isoformat()}
    await db.broker_connections.update_one(
        {"user_id": user["id"], "broker": "oanda"}, {"$set": row}, upsert=True)
    return {"broker": "oanda", "environment": "practice", "connected": True,
            "account_hint": row["key_hint"], "currency": account.get("currency")}

@router.get("/account")
async def account(user: dict = Depends(get_current_user)):
    account_id, token = await _credentials(user["id"])
    summary = await oanda_get(f"/v3/accounts/{account_id}/summary", token)
    positions = await oanda_get(f"/v3/accounts/{account_id}/openPositions", token)
    orders = await oanda_get(f"/v3/accounts/{account_id}/pendingOrders", token)
    info = summary.get("account") if isinstance(summary, dict) else None
    if (not isinstance(info, dict) or not isinstance(positions, dict) or not isinstance(orders, dict)\n            or not isinstance(positions.get("positions"), list) or not isinstance(orders.get("orders"), list)):
        raise HTTPException(502, "Unexpected OANDA response format")
    return {"broker": "oanda", "environment": "practice", "source": "oanda_v20_practice_api",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "account": _only(info, ("id", "currency", "balance", "NAV", "marginAvailable",
                                     "marginUsed", "unrealizedPL", "pl", "openTradeCount", "pendingOrderCount")),
            "positions": [_only(p, ("instrument", "long", "short", "unrealizedPL", "pl")) for p in positions["positions"]],
            "orders": [_only(o, ("id", "instrument", "units", "type", "state", "createTime",
                                "price", "timeInForce")) for o in orders["orders"]]}

@router.delete("")
async def disconnect(user: dict = Depends(get_current_user)):
    await db.broker_connections.delete_many({"user_id": user["id"], "broker": "oanda"})
    return {"broker": "oanda", "connected": False}
