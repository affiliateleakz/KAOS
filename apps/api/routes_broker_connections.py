"""Member broker connection registry.

`/dashboard/brokers` has always called these three endpoints, but no router ever
implemented them, so saving a Coinbase key returned 404 and the page stayed empty.
Credentials are verified against the broker, encrypted with the server vault
(`broker_vault`, same key ring `routes_coinbase` decrypts with) and never returned
to a client. Only a masked hint is disclosed.
"""
import asyncio

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth import get_current_user
from broker_vault import vault
from db import db, now_iso
from services import audit_log

router = APIRouter(prefix="/api/v1/broker-connections", tags=["broker-connections"])

SUPPORTED = ("coinbase",)


class CoinbaseCredentials(BaseModel):
    key_name: str = Field(min_length=8, max_length=512)
    private_key: str = Field(min_length=32, max_length=8192)


def _hint(key_name: str) -> str:
    """Last four characters only: enough to recognise a key, useless to an attacker."""
    tail = key_name.strip()[-4:]
    return f"…{tail}" if tail else "••••"


def _public(row: dict) -> dict:
    return {
        "broker": row["broker"],
        "saved": True,
        "verified": bool(row.get("verified")),
        "key_hint": row.get("key_hint") or "••••",
        "updated_at": row.get("updated_at"),
    }


async def _verify_coinbase(key_name: str, private_key: str) -> None:
    """Prove the credentials work before storing them. Fails closed."""
    def call():
        from coinbase.rest import RESTClient
        client = RESTClient(api_key=key_name, api_secret=private_key, timeout=12)
        return client.get_accounts(limit=1)

    try:
        await asyncio.to_thread(call)
    except ImportError:
        raise HTTPException(503, "Coinbase verification is unavailable on this server")
    except Exception:
        raise HTTPException(400, "Coinbase rejected these credentials")


@router.get("")
async def list_connections(user: dict = Depends(get_current_user)):
    rows = await db.broker_connections.find({"user_id": user["id"]}, {"_id": 0}).to_list(20)
    return {"connections": [_public(r) for r in rows], "supported": list(SUPPORTED)}


@router.put("/coinbase")
async def save_coinbase(body: CoinbaseCredentials, user: dict = Depends(get_current_user)):
    if user.get("account_status", "active") != "active" or user.get("extension_access_revoked"):
        raise HTTPException(403, "Account disabled")
    key_name, private_key = body.key_name.strip(), body.private_key.strip()
    # Resolve the vault first: if the server cannot encrypt, never accept the secret.
    fernet = vault()
    await _verify_coinbase(key_name, private_key)
    doc = {
        "user_id": user["id"],
        "broker": "coinbase",
        "saved": True,
        "verified": True,
        "key_name_enc": fernet.encrypt(key_name.encode()).decode(),
        "private_key_enc": fernet.encrypt(private_key.encode()).decode(),
        "key_hint": _hint(key_name),
        "updated_at": now_iso(),
    }
    await db.broker_connections.update_one(
        {"user_id": user["id"], "broker": "coinbase"}, {"$set": doc}, upsert=True
    )
    await audit_log(user, "broker_connection_saved", "broker", "coinbase")
    return _public(doc)


@router.delete("/coinbase")
async def delete_coinbase(user: dict = Depends(get_current_user)):
    result = await db.broker_connections.delete_one({"user_id": user["id"], "broker": "coinbase"})
    if not result.deleted_count:
        raise HTTPException(404, "No saved Coinbase connection")
    await audit_log(user, "broker_connection_removed", "broker", "coinbase")
    return {"broker": "coinbase", "saved": False}
