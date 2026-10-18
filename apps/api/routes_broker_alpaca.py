"""Alpaca Trading API read-only connection. Paper endpoint only; never sends orders.

Requires founder/member-provided Alpaca PAPER API key and secret, entered into KAOS.
Credentials are encrypted at rest; no outbound requests to a live trading endpoint.
"""
from datetime import datetime, timezone
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from auth import get_current_user
from db import db
import broker_vault

router = APIRouter(prefix="/api/v1/broker-connections/alpaca", tags=["brokers"])
PAPER_URL = "https://paper-api.alpaca.markets"
TIMEOUT = 12.0

class ConnectRequest(BaseModel):
    api_key: str = Field(min_length=8, max_length=256)
    api_secret: str = Field(min_length=8, max_length=512)

async def alpaca_get(path: str, key: str, secret: str):
    if path not in ("/v2/account", "/v2/positions", "/v2/orders"):
        raise HTTPException(400, "Unsupported Alpaca account endpoint")
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=False) as client:
            res = await client.get(PAPER_URL + path, headers={
                "APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret,
                "Accept": "application/json"})
        if res.status_code in (401, 403):
            raise HTTPException(422, "Alpaca paper credentials rejected or account access denied")
        if res.status_code != 200:
            raise HTTPException(502, "Alpaca paper account data unavailable")
        return res.json()
    except HTTPException:
        raise
    except (httpx.HTTPError, ValueError):
        raise HTTPException(502, "Alpaca paper API unavailable")

def _fields(data, names):
    return {k: data.get(k) for k in names if k in data}

async def _credentials(user_id):
    row = await db.broker_connections.find_one(
        {"user_id": user_id, "broker": "alpaca", "verified": True})
    if not row:
        raise HTTPException(404, "No Alpaca paper account connected")
    try:
        v = broker_vault.vault()
        return v.decrypt(row["key_name_enc"].encode()).decode(), v.decrypt(row["private_key_enc"].encode()).decode()
    except Exception:
        raise HTTPException(503, "Alpaca credentials unavailable; reconnect")

@router.put("")
async def connect(req: ConnectRequest, user: dict = Depends(get_current_user)):
    key, secret = req.api_key.strip(), req.api_secret.strip()
    if not key or not secret:
        raise HTTPException(422, "API key and secret required")
    v = broker_vault.vault()
    account = await alpaca_get("/v2/account", key, secret)
    if not isinstance(account, dict) or not account.get("id"):
        raise HTTPException(502, "Alpaca account verification failed")
    row = {"user_id": user["id"], "broker": "alpaca", "verified": True,
           "key_name_enc": v.encrypt(key.encode()).decode(),
           "private_key_enc": v.encrypt(secret.encode()).decode(),
           "key_hint": "…" + key[-4:], "permissions": {"can_view": True, "can_trade": False, "can_transfer": False},
           "environment": "paper", "connected_at": datetime.now(timezone.utc).isoformat()}
    await db.broker_connections.update_one(
        {"user_id": user["id"], "broker": "alpaca"}, {"$set": row}, upsert=True)
    return {"broker": "alpaca", "environment": "paper", "connected": True,
            "key_hint": row["key_hint"], "account_status": account.get("status")}

@router.get("/account")
async def account(user: dict = Depends(get_current_user)):
    key, secret = await _credentials(user["id"])
    account_data = await alpaca_get("/v2/account", key, secret)
    positions_data = await alpaca_get("/v2/positions", key, secret)
    orders_data = await alpaca_get("/v2/orders", key, secret)
    if not isinstance(account_data, dict) or not isinstance(positions_data, list) or not isinstance(orders_data, list):
        raise HTTPException(502, "Unexpected Alpaca response format")
    return {"broker": "alpaca", "environment": "paper", "source": "alpaca_paper_trading_api",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "account": _fields(account_data, ("id", "status", "currency", "cash", "buying_power", "equity",
                                             "portfolio_value", "pattern_day_trader", "trading_blocked")),
            "positions": [_fields(p, ("symbol", "asset_id", "qty", "side", "market_value", "cost_basis",
                                     "avg_entry_price", "current_price", "unrealized_pl")) for p in positions_data],
            "orders": [_fields(o, ("id", "client_order_id", "symbol", "side", "qty", "filled_qty",
                                  "type", "status", "filled_avg_price", "created_at", "filled_at")) for o in orders_data]}

@router.delete("")
async def disconnect(user: dict = Depends(get_current_user)):
    await db.broker_connections.delete_many({"user_id": user["id"], "broker": "alpaca"})
    return {"broker": "alpaca", "connected": False}
