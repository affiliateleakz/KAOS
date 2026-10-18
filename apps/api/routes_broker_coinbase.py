"""Coinbase Advanced account connection (read-only views).

Members connect their own CDP API key. Keys are encrypted with KAOS_BROKER_VAULT_KEY,
verified against Coinbase's key-permission endpoint, and never returned to clients.
Keys with transfer permission are refused. Nothing here places or cancels orders;
live order submission lives in routes_coinbase and stays disabled by default.
"""
import asyncio
import json
import os
import re
import time
from datetime import datetime, timezone
from typing import Callable

from cryptography.fernet import Fernet, InvalidToken
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth import get_current_user
from db import db
from services import audit_log

router = APIRouter(prefix="/api/v1/broker-connections", tags=["brokers"])
KEY_NAME = re.compile(r"^organizations/[A-Za-z0-9-]{1,64}/apiKeys/[A-Za-z0-9-]{1,64}$")
UUID_KEY = re.compile(r"^[0-9a-fA-F-]{36}$")
ED25519 = re.compile(r"^[A-Za-z0-9+/]{80,90}={0,2}$")
CACHE_SECONDS = 5
_cache: dict = {}


class ConnectReq(BaseModel):
    key_name: str = Field(max_length=200)
    private_key: str = Field(max_length=4000)


def _make_rest_client(key_name: str, private_key: str):
    from coinbase.rest import RESTClient
    return RESTClient(api_key=key_name, api_secret=private_key, timeout=12)


client_factory: Callable = _make_rest_client


def _vault() -> Fernet:
    key = os.environ.get("KAOS_BROKER_VAULT_KEY")
    if not key:
        raise HTTPException(503, "Broker vault not configured on this server")
    return Fernet(key.encode())


def _d(value):
    if hasattr(value, "to_dict"):
        return value.to_dict()
    return value if isinstance(value, dict) else {}


async def _call(fn, *args, **kwargs):
    try:
        return _d(await asyncio.to_thread(fn, *args, **kwargs))
    except HTTPException:
        raise
    except Exception as exc:  # Coinbase/network errors; never echo request details (they include signed JWTs)
        raise HTTPException(502, f"Coinbase request failed ({type(exc).__name__})")


async def _row(user_id: str) -> dict:
    row = await db.broker_connections.find_one({"user_id": user_id, "broker": "coinbase", "verified": True}, {"_id": 0})
    if not row:
        raise HTTPException(404, "No Coinbase account connected")
    return row


def _client_for(row: dict):
    v = _vault()
    try:
        return client_factory(v.decrypt(row["key_name_enc"].encode()).decode(),
                              v.decrypt(row["private_key_enc"].encode()).decode())
    except InvalidToken:
        raise HTTPException(503, "Stored Coinbase credentials cannot be decrypted; reconnect the account")


def _public(row: dict) -> dict:
    return {"connected": True, "broker": "coinbase", "key_hint": row.get("key_hint"),
            "permissions": row.get("permissions"), "portfolio_type": row.get("portfolio_type"),
            "connected_at": row.get("connected_at"),
            "live_orders_enabled": os.getenv("KAOS_COINBASE_LIVE_ORDERS", "disabled") == "enabled"}


@router.put("/coinbase")
async def connect(req: ConnectReq, user: dict = Depends(get_current_user)):
    key_name, private_key = req.key_name.strip(), req.private_key.strip()
    if private_key.startswith("{"):  # downloaded cdp_api_key.json
        try:
            blob = json.loads(private_key)
            key_name, private_key = blob.get("name") or key_name, blob["privateKey"].strip()
        except (ValueError, KeyError, AttributeError):
            raise HTTPException(422, "Credentials JSON must contain name and privateKey")
    private_key = private_key.replace("\\n", "\n")
    if not (KEY_NAME.fullmatch(key_name) or UUID_KEY.fullmatch(key_name)):
        raise HTTPException(422, "Key name must look like organizations/<org>/apiKeys/<key>")
    if "PRIVATE KEY-----" not in private_key and not ED25519.fullmatch(private_key):
        raise HTTPException(422, "Private key must be the ECDSA PEM or Ed25519 key shown when the API key was created")
    vault = _vault()
    probe = client_factory(key_name, private_key)
    perms = await _call(probe.get_api_key_permissions)
    if not perms.get("can_view"):
        raise HTTPException(422, "Key lacks View permission")
    if perms.get("can_transfer"):
        raise HTTPException(422, "Refused: this key can transfer funds. Create a key without Transfer permission.")
    now = datetime.now(timezone.utc).isoformat()
    row = {"user_id": user["id"], "broker": "coinbase", "verified": True,
           "key_name_enc": vault.encrypt(key_name.encode()).decode(),
           "private_key_enc": vault.encrypt(private_key.encode()).decode(),
           "key_hint": "…" + key_name[-4:],
           "permissions": {"can_view": True, "can_trade": bool(perms.get("can_trade")), "can_transfer": False},
           "portfolio_type": perms.get("portfolio_type"), "portfolio_uuid": perms.get("portfolio_uuid"),
           "connected_at": now}
    await db.broker_connections.update_one({"user_id": user["id"], "broker": "coinbase"}, {"$set": row}, upsert=True)
    _cache.pop(user["id"], None)
    accounts = await _call(probe.get_accounts, limit=250)
    await audit_log(user, "broker.coinbase.connect", "broker_connection", user["id"],
                    {"key_hint": row["key_hint"], "can_trade": row["permissions"]["can_trade"]})
    return {**_public(row), "account_count": len(accounts.get("accounts", []))}


@router.get("/coinbase/status")
async def status(user: dict = Depends(get_current_user)):
    row = await db.broker_connections.find_one({"user_id": user["id"], "broker": "coinbase", "verified": True}, {"_id": 0})
    pub = _public(row) if row else {"connected": False, "broker": "coinbase"}
    return {**pub, "connection": {"saved": bool(row), "verified": bool(row), "key_hint": (row or {}).get("key_hint")}}


@router.get("")
async def list_connections(user: dict = Depends(get_current_user)):
    rows = await db.broker_connections.find({"user_id": user["id"]}, {"_id": 0, "broker": 1, "verified": 1, "key_hint": 1,
                                                                      "permissions": 1, "connected_at": 1}).to_list(20)
    fields = ("broker", "verified", "key_hint", "permissions", "connected_at")
    return {"connections": [{**{k: r.get(k) for k in fields}, "saved": True} for r in rows]}


@router.delete("/coinbase")
async def disconnect(user: dict = Depends(get_current_user)):
    await db.broker_connections.delete_many({"user_id": user["id"], "broker": "coinbase"})
    _cache.pop(user["id"], None)
    await audit_log(user, "broker.coinbase.disconnect", "broker_connection", user["id"])
    return {"connected": False, "broker": "coinbase"}


def _num(v):
    return (v or {}).get("value", "0") if isinstance(v, dict) else (v or "0")


@router.get("/coinbase/accounts")
async def account(user: dict = Depends(get_current_user)):
    """Balances, open orders, recent fills and fee tier straight from Coinbase (cached 5 s per member)."""
    hit = _cache.get(user["id"])
    if hit and time.monotonic() - hit[0] < CACHE_SECONDS:
        return hit[1]
    row = await _row(user["id"])
    c = _client_for(row)
    accts, opened, fills, fees = await asyncio.gather(
        _call(c.get_accounts, limit=250), _call(c.list_orders, order_status=["OPEN"], limit=50),
        _call(c.get_fills, limit=50), _call(c.get_transaction_summary))
    balances = []
    for a in accts.get("accounts", []):
        avail, hold = _num(a.get("available_balance")), _num(a.get("hold"))
        if float(avail) or float(hold):
            balances.append({"currency": a.get("currency"), "available": avail, "hold": hold})
    keep = ("order_id", "client_order_id", "product_id", "side", "status", "order_type", "created_time",
            "filled_size", "average_filled_price", "total_fees", "completion_percentage")
    tier = fees.get("fee_tier") or {}
    out = {"source": "coinbase_advanced_api", "fetched_at": datetime.now(timezone.utc).isoformat(),
           "key_hint": row.get("key_hint"), "balances": balances,
           "open_orders": [{k: o.get(k) for k in keep} for o in opened.get("orders", [])],
           "fills": [{k: f.get(k) for k in ("entry_id", "trade_id", "order_id", "product_id", "side", "price", "size",
                                             "commission", "trade_time", "liquidity_indicator")} for f in fills.get("fills", [])],
           "fees": {"tier": tier.get("pricing_tier"), "maker_rate": tier.get("maker_fee_rate"),
                    "taker_rate": tier.get("taker_fee_rate"), "total_fees": fees.get("total_fees"),
                    "total_volume": fees.get("total_volume")}}
    _cache[user["id"]] = (time.monotonic(), out)
    return out


@router.get("/coinbase/products")
async def products(user: dict = Depends(get_current_user)):
    """USD spot markets visible to the connected account, with Coinbase's own price and 24h change."""
    c = _client_for(await _row(user["id"]))
    data = await _call(c.get_products, product_type="SPOT", limit=500)
    keep = ("product_id", "price", "price_percentage_change_24h", "volume_24h", "quote_increment", "base_min_size",
            "trading_disabled", "status")
    return {"source": "coinbase_advanced_api", "products": [{k: p.get(k) for k in keep} for p in data.get("products", [])
                                                           if p.get("quote_currency_id") == "USD"]}
