"""Admin data-integration controls for the Market Intelligence Centre.

Only enable/disable flags and credential *presence* are exposed; secret values
never leave the server. Disabling a source makes the member scanners report
``disabled_by_admin`` instead of returning rows.
"""
import os
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import require_role
from db import db
from services import audit_log, get_setting, set_setting

router = APIRouter(prefix="/api/admin/intelligence", tags=["admin-intelligence"])
admin_dep = require_role("admin")

SOURCES = {
    "coinbase_public": {
        "name": "Coinbase Exchange public candles", "kind": "request_time",
        "required_env": [], "event_prefixes": [],
        "note": "No key required. Public spot candles only.",
    },
    "alpaca": {
        "name": "Alpaca Market Data (stocks/ETFs)", "kind": "request_time",
        "required_env": ["APCA_API_KEY_ID", "APCA_API_SECRET_KEY"],
        "event_prefixes": ["alpaca"],
        "note": "Free market-data key. IEX feed by default; spend no money automatically.",
    },
    "bluesky": {
        "name": "Bluesky public search and feeds", "kind": "collector", "required_env": [],
        "event_prefixes": ["bsky-social", "bsky-search"],
        "note": "Bounded public samples, not platform-wide mentions.",
    },
    "tradier": {
        "name": "Tradier options chains", "kind": "collector",
        "required_env": ["TRADIER_TOKEN"], "event_prefixes": ["option-volume-rise"],
        "note": "Sandbox chains are delayed; no Greeks are stored.",
    },
    "gdelt": {
        "name": "GDELT news mentions", "kind": "collector", "required_env": [],
        "event_prefixes": ["gdelt"], "note": "First-seen timestamps, not verified publication time.",
    },
    "sec": {
        "name": "SEC EDGAR filings, Form 4, 13F", "kind": "collector", "required_env": [],
        "event_prefixes": ["sec", "sec-form4-txn", "sec13f"],
        "note": "Delayed filings; parses are limited to what the collector extraction supports.",
    },
    "onchain": {
        "name": "Ethereum and DEX on-chain observations", "kind": "collector", "required_env": [],
        "event_prefixes": ["eth-mainnet", "dexscreener"],
        "note": "Transfers do not establish wallet ownership or trade direction.",
    },
    "binance": {
        "name": "Binance public spot candles", "kind": "collector", "required_env": [],
        "event_prefixes": ["binance-spot"],
        "note": "Exchange spot data is not Pocket Option OTC pricing.",
    },
}


class SourceToggle(BaseModel):
    enabled: bool


@router.get("/sources")
async def list_sources(admin: dict = Depends(admin_dep)):
    settings = await get_setting("intel_sources", {}) or {}
    rows = []
    for key, meta in SOURCES.items():
        last = None
        prefixes = meta["event_prefixes"]
        if prefixes:
            query = {"$or": [{"event_id": {"$regex": "^" + re.escape(p) + ":"}} for p in prefixes]}
            doc = await db.kaos_intelligence.find_one(
                query, {"_id": 0, "event_id": 1, "observed_at": 1, "asset_class": 1},
                sort=[("observed_at", -1)])
            if doc:
                last = {"event_id": doc.get("event_id"), "observed_at": doc.get("observed_at"),
                        "asset_class": doc.get("asset_class")}
        missing = [name for name in meta["required_env"] if not os.environ.get(name)]
        rows.append({
            "provider": key,
            "name": meta["name"],
            "kind": meta["kind"],
            "enabled": settings.get(key, True) is not False,
            "configured": not missing,
            "missing_env": missing,
            "last_observation": last,
            "note": meta["note"],
        })
    return {
        "sources": rows,
        "collector_configured": bool(os.environ.get("KAOS_COLLECTOR_KEY")),
        "credentials_exposed": False,
        "allows_paid_providers": False,
        "note": ("KAOS uses free or owner-supplied credentials only. Toggling a source "
                 "stops member scanner rows for it; it never deletes stored observations."),
    }


@router.put("/sources/{provider}")
async def toggle_source(provider: str, body: SourceToggle, admin: dict = Depends(admin_dep)):
    if provider not in SOURCES:
        raise HTTPException(404, "Unknown intelligence source")
    settings = dict(await get_setting("intel_sources", {}) or {})
    settings[provider] = bool(body.enabled)
    await set_setting("intel_sources", settings)
    await audit_log(admin, "intel_source_toggle", "intel_source", provider,
                    {"enabled": bool(body.enabled)})
    return {"provider": provider, "enabled": bool(body.enabled),
            "credentials_exposed": False}
