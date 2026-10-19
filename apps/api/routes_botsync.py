"""Extension auth aliases, bot config/release/platforms, and idempotent event ingestion."""
from typing import Optional, List
from pydantic import BaseModel
from fastapi import APIRouter, Depends, Request, HTTPException
from db import db, new_id, now_iso, clean
from auth import get_current_user
from services import compute_license, get_setting
from services_trading import get_official_strategy, get_entitlements, DEFAULT_CONNECTORS, TRADE_STATES

# Event types the cloud will accept & store. Anything outside this lifecycle set is rejected so
# malformed/unknown types can't pollute trade_events / sync-status statistics.
ALLOWED_EVENT_TYPES = set(TRADE_STATES)
import routes_extension as rx

bot = APIRouter(prefix="/api/v1", tags=["bot-sync"])


# Extension auth aliases (delegate to existing v1 auth for a stable bot-facing surface)
@bot.post("/extension/login")
async def ext_login(req: rx.LoginReq):
    return await rx.v1_login(req)


@bot.post("/extension/refresh")
async def ext_refresh(request: Request):
    return await rx.v1_refresh(request)


@bot.post("/extension/logout")
async def ext_logout(user: dict = Depends(get_current_user)):
    return {"ok": True}


@bot.get("/extension/me")
async def ext_me(request: Request, user: dict = Depends(get_current_user)):
    did = request.headers.get("X-Device-Id")
    device = await db.devices.find_one({"installId": did, "userId": user["id"]}) if did else None
    if device and device.get("revoked"):
        raise HTTPException(status_code=403, detail="Device access revoked")
    # An unregistered device can still read onboarding status before registration.
    # The license/status and device-registration endpoints enforce device access.
    # Broker selection precedes broker-specific eligibility checks.
    # In particular, a member choosing Coinbase must not be blocked by
    # Pocket Option's separate affiliate verification requirement.
    selection = await db.member_broker_selections.find_one(
        {"user_id": user["id"]}, {"_id": 0, "broker": 1})
    selected_broker = (selection or {}).get("broker")
    broker_for_license = "pocket_option" if selected_broker in ("pocketoption", "pocket_option") else (selected_broker or "unselected")
    lic = await compute_license(user, device, broker=broker_for_license)
    ent = await get_entitlements(user)
    return {"user": {"id": user["id"], "username": user.get("username"), "email": user["email"], "role": user.get("role")},
            "license": lic, "entitlements": ent}


@bot.get("/bot/config")
async def bot_config(user: dict = Depends(get_current_user)):
    return {"entitlements": await get_entitlements(user),
            "officialStrategy": await get_official_strategy(),
            "collectiveLearningConsent": bool(user.get("collective_learning_consent", False)),
            "tradingMode": user.get("trading_mode", "STRATEGY")}


@bot.get("/bot/release")
async def bot_release():
    rel = await db.extension_releases.find_one({"published": True}, {"_id": 0}, sort=[("createdAt", -1)])
    return rel or {"version": None}


@bot.get("/platforms")
async def platforms():
    return await get_setting("connectors", DEFAULT_CONNECTORS)


class TradeEvent(BaseModel):
    eventId: str          # stable client id -> idempotent
    type: str             # lifecycle event name
    signalId: Optional[str] = None
    tradeId: Optional[str] = None
    payload: dict = {}
    timestamp: Optional[str] = None


class EventsBatch(BaseModel):
    events: List[TradeEvent]


@bot.post("/trading/events")
async def ingest_events(batch: EventsBatch, user: dict = Depends(get_current_user)):
    """Idempotent event ingestion. A lost ACK causes a safe retry; duplicates are deduped by eventId.
    This is a CLOUD-SYNC channel only and never triggers a broker order."""
    from routes_trading import chart_limit_error
    acked, duplicates, rejected = [], [], []
    ent = None
    for e in batch.events:
        # Reject unknown/malformed event types up front (keeps stats & sync-status clean).
        if e.type not in ALLOWED_EVENT_TYPES:
            rejected.append({"eventId": e.eventId, "type": e.type, "reason": "unknown_event_type"})
            continue
        slot = (e.payload or {}).get("chartSlot")
        if slot is not None:
            ent = ent or await get_entitlements(user)
            if chart_limit_error(ent, slot):
                rejected.append({"eventId": e.eventId, "type": e.type, "reason": "chart_limit"})
                continue
        if await db.trade_events.find_one({"eventId": e.eventId}):
            duplicates.append(e.eventId)
            continue
        await db.trade_events.insert_one({"eventId": e.eventId, "userId": user["id"], "type": e.type,
                                          "signalId": e.signalId, "tradeId": e.tradeId, "payload": e.payload,
                                          "timestamp": e.timestamp or now_iso(), "createdAt": now_iso()})
        acked.append(e.eventId)
    return {"acked": acked, "duplicates": duplicates, "rejected": rejected, "serverTime": now_iso()}


class ConsentReq(BaseModel):
    consent: bool


@bot.post("/ai/consent")
async def set_consent(req: ConsentReq, user: dict = Depends(get_current_user)):
    await db.users.update_one({"id": user["id"]}, {"$set": {"collective_learning_consent": req.consent, "updated_at": now_iso()}})
    return {"collectiveLearningConsent": req.consent}
