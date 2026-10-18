"""Alpaca account connection (read-only views).

Alpaca API keys cannot be limited to read-only, so KAOS never calls an Alpaca order endpoint from here.
Paper accounts are the default; a live-account key is accepted for viewing only when the member says so.
Keys are encrypted with the broker vault and never returned to clients.
"""
import os
from datetime import datetime, timezone

import httpx
from cryptography.fernet import InvalidToken
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth import get_current_user
from db import db
from services import audit_log
import broker_vault

router = APIRouter(prefix="/api/v1/broker-connections", tags=["brokers"])
HOSTS = {"paper": "https://paper-api.alpaca.markets", "live": "https://api.alpaca.markets"}
transport = None  # tests inject httpx.MockTransport


class AlpacaConnect(BaseModel):
    key_id: str = Field(min_length=10, max_length=64, pattern=r"^[A-Z0-9]+$")
    secret_key: str = Field(min_length=20, max_length=128)
    environment: str = Field(default="paper", pattern=r"^(paper|live)$")


async def _get(env, key_id, secret, path, params=None):
    headers = {"APCA-API-KEY-ID": key_id, "APCA-API-SECRET-KEY": secret}
    try:
        async with httpx.AsyncClient(base_url=HOSTS[env], headers=headers, timeout=12, transport=transport) as c:
            r = await c.get(path, params=params)
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"Alpaca request failed ({type(exc).__name__})")
    if r.status_code in (401, 403):
        raise HTTPException(422, "Alpaca rejected the key (check key, secret and paper/live environment)")
    if r.status_code >= 400:
        raise HTTPException(502, f"Alpaca request failed (HTTP {r.status_code})")
    return r.json()


def _public(row):
    return {"connected": True, "broker": "alpaca", "key_hint": row.get("key_hint"), "environment": row.get("environment"),
            "connected_at": row.get("connected_at"), "live_orders_enabled": False}


async def _creds(uid):
    row = await db.broker_connections.find_one({"user_id": uid, "broker": "alpaca", "verified": True}, {"_id": 0})
    if not row:
        raise HTTPException(404, "No Alpaca account connected")
    v = broker_vault.vault()
    try:
        return row, v.decrypt(row["key_name_enc"].encode()).decode(), v.decrypt(row["private_key_enc"].encode()).decode()
    except InvalidToken:
        raise HTTPException(503, "Stored Alpaca credentials cannot be decrypted; reconnect the account")


@router.put("/alpaca")
async def connect(req: AlpacaConnect, user: dict = Depends(get_current_user)):
    vault = broker_vault.vault()
    acct = await _get(req.environment, req.key_id, req.secret_key, "/v2/account")
    if acct.get("status") != "ACTIVE":
        raise HTTPException(422, f"Alpaca account is not active ({acct.get('status')})")
    row = {"user_id": user["id"], "broker": "alpaca", "verified": True, "environment": req.environment,
           "key_name_enc": vault.encrypt(req.key_id.encode()).decode(),
           "private_key_enc": vault.encrypt(req.secret_key.encode()).decode(),
           "key_hint": "…" + req.key_id[-4:], "permissions": {"can_view": True, "can_trade": "not_used_by_kaos"},
           "connected_at": datetime.now(timezone.utc).isoformat()}
    await db.broker_connections.update_one({"user_id": user["id"], "broker": "alpaca"}, {"$set": row}, upsert=True)
    await audit_log(user, "broker.alpaca.connect", "broker_connection", user["id"],
                    {"key_hint": row["key_hint"], "environment": req.environment})
    return _public(row)


@router.get("/alpaca/status")
async def status(user: dict = Depends(get_current_user)):
    row = await db.broker_connections.find_one({"user_id": user["id"], "broker": "alpaca", "verified": True}, {"_id": 0})
    return _public(row) if row else {"connected": False, "broker": "alpaca"}


@router.delete("/alpaca")
async def disconnect(user: dict = Depends(get_current_user)):
    await db.broker_connections.delete_many({"user_id": user["id"], "broker": "alpaca"})
    await audit_log(user, "broker.alpaca.disconnect", "broker_connection", user["id"])
    return {"connected": False, "broker": "alpaca"}


@router.get("/alpaca/accounts")
async def account(user: dict = Depends(get_current_user)):
    """Account, positions (Alpaca computes P&L), open orders and recent fills, straight from Alpaca."""
    row, key, secret = await _creds(user["id"])
    env = row["environment"]
    acct = await _get(env, key, secret, "/v2/account")
    positions = await _get(env, key, secret, "/v2/positions")
    orders = await _get(env, key, secret, "/v2/orders", {"status": "open", "limit": 100})
    fills = await _get(env, key, secret, "/v2/account/activities/FILL", {"page_size": 50})
    return {"source": "alpaca_trading_api", "environment": env, "key_hint": row.get("key_hint"),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "account": {k: acct.get(k) for k in ("status", "currency", "cash", "buying_power", "equity", "portfolio_value",
                                                  "pattern_day_trader", "trading_blocked", "daytrade_count")},
            "positions": [{k: p.get(k) for k in ("symbol", "asset_class", "qty", "side", "avg_entry_price", "current_price",
                                                 "market_value", "unrealized_pl", "unrealized_plpc")} for p in positions],
            "open_orders": [{k: o.get(k) for k in ("id", "client_order_id", "symbol", "side", "type", "qty", "notional",
                                                   "limit_price", "status", "filled_qty", "submitted_at")} for o in orders],
            "fills": [{k: f.get(k) for k in ("id", "order_id", "symbol", "side", "qty", "price", "transaction_time")} for f in fills],
            "fees_note": "Alpaca charges no commission on US stocks/ETFs; regulatory fees appear as separate account activities."}
