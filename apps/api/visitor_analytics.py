"""First-party visitor analytics. Aggregated affiliate scope; no raw IPs or query strings."""

import asyncio
from datetime import timedelta
import hashlib
import hmac
import os
import re
from typing import Literal
from urllib.parse import urlsplit
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field
from pymongo.errors import DuplicateKeyError
from db import db, now, now_iso
from auth import get_current_user, require_role
from analytics_geo import client_address, country, source_info

router = APIRouter(tags=["visitor analytics"])
ADMIN = require_role("admin")
_ready = False
_lock = asyncio.Lock()
RETENTION_DAYS = 90


class Visit(BaseModel):
    eventId: UUID
    visitorId: UUID
    sessionId: UUID
    kind: Literal["pageview", "click"] = "pageview"
    path: str = Field(max_length=500)
    target: str = Field(default="", max_length=500)
    ref: str | None = Field(default=None, max_length=128)
    source: str = Field(default="", max_length=80)
    medium: str = Field(default="", max_length=80)
    campaign: str = Field(default="", max_length=100)
    referrer: str = Field(default="", max_length=1000)
    entry: bool = False


def digest(value):
    secret = os.getenv("JWT_SECRET", "")
    if not secret:
        raise HTTPException(503, "Analytics is temporarily unavailable")
    return hmac.new(
        secret.encode(), ("kaos-analytics:" + value).encode(), hashlib.sha256
    ).hexdigest()


def label(value, maximum=100):
    return re.sub(r"[^a-zA-Z0-9_. -]", "", str(value or ""))[:maximum].strip()


def path_label(value):
    # Never retain query parameters, account IDs, tokens, emails, or private page paths.
    try:
        path = urlsplit(value).path
    except ValueError:
        return "/other"
    parts = path.strip("/").split("/")
    public = {
        "",
        "register",
        "checkout",
        "login",
        "memberships",
        "privacy",
        "privacy.html",
        "payment",
        "dashboard",
        "share",
        "s",
        "community",
    }
    if parts[0] not in public:
        return "/other"
    if parts[0] in ("share", "s", "community"):
        return "/" + parts[0]
    if parts[0] in ("payment", "dashboard", "register"):
        return (
            "/"
            + parts[0]
            + (
                "/" + parts[1]
                if len(parts) > 1
                and parts[1]
                in {
                    "account",
                    "complete",
                    "success",
                    "cancel",
                    "subscription",
                    "affiliate",
                    "trading",
                    "strategies",
                    "community",
                    "radar",
                    "profile",
                }
                else ""
            )
        )
    return "/" + parts[0]


def host_label(value):
    try:
        parsed = urlsplit(value)
        if parsed.scheme not in ("https", "http") or parsed.username or parsed.password:
            return ""
        return (parsed.hostname or "").lower().removeprefix("www.")[:180]
    except ValueError:
        return ""


def source_labels(payload):
    referrer = host_label(payload.referrer)
    own = host_label(os.getenv("FRONTEND_URL", "https://tradingwithkaos.com"))
    return {
        "source": label(payload.source, 80).lower()
        or (referrer if referrer and referrer != own else "direct"),
        "medium": label(payload.medium, 80).lower()
        or ("referral" if referrer and referrer != own else "none"),
        "campaign": label(payload.campaign),
        "referrerHost": referrer if referrer != own else "",
    }


async def indexes():
    global _ready
    if _ready:
        return
    async with _lock:
        if _ready:
            return
        await db.visitor_events.create_index("expiresAt", expireAfterSeconds=0)
        await db.visitor_events.create_index([("createdAt", -1)])
        await db.visitor_events.create_index([("refCode", 1), ("createdAt", -1)])
        await db.visitor_sessions.create_index("expiresAt", expireAfterSeconds=0)
        await db.visitor_limits.create_index("expiresAt", expireAfterSeconds=0)
        await db.visitor_entries.create_index("expiresAt", expireAfterSeconds=0)
        await db.users.create_index("referredByCode")
        await db.affiliate_click_totals.create_index("code")
        _ready = True


async def rate_limit(request):
    key = digest(
        "rate:" + client_address(request) + ":" + str(int(now().timestamp() // 600))
    )
    try:
        await db.visitor_limits.update_one(
            {"_id": key, "count": {"$lt": 240}},
            {
                "$inc": {"count": 1},
                "$setOnInsert": {"expiresAt": now() + timedelta(hours=1)},
            },
            upsert=True,
        )
    except DuplicateKeyError:
        raise HTTPException(429, "Analytics rate limit reached") from None


@router.post("/api/analytics/visit")
async def capture(payload: Visit, request: Request, response: Response):
    response.headers["Cache-Control"] = "no-store"
    if request.headers.get("dnt") == "1" or request.headers.get("sec-gpc") == "1":
        return {"recorded": False}
    if re.search(
        r"bot|crawler|spider|preview|facebookexternalhit",
        request.headers.get("user-agent", ""),
        re.I,
    ):
        return {"recorded": False}
    await indexes()
    await rate_limit(request)
    visitor = digest("visitor:" + str(payload.visitorId))
    session = digest("session:" + str(payload.visitorId) + ":" + str(payload.sessionId))
    event = digest("event:" + visitor + ":" + str(payload.eventId))
    acc = (
        await db.affiliate_accounts.find_one(
            {"code": payload.ref}, {"code": 1, "userId": 1}
        )
        if payload.ref
        else None
    )
    ref = acc["code"] if acc else None
    stamp = now()
    expires = stamp + timedelta(days=RETENTION_DAYS)
    acquisition = {
        **source_labels(payload),
        "country": country(client_address(request)),
        "path": path_label(payload.path),
        "refCode": ref,
    }
    await db.visitor_sessions.update_one(
        {"_id": session},
        {
            "$setOnInsert": {"visitor": visitor, **acquisition, "createdAt": stamp},
            "$set": {"expiresAt": expires},
        },
        upsert=True,
    )
    # Use the session's original acquisition source on later navigation.
    saved = await db.visitor_sessions.find_one({"_id": session})
    acquisition = {k: saved.get(k, acquisition.get(k)) for k in acquisition}
    if ref:
        acquisition["refCode"] = ref
    entry = False
    if payload.kind == "pageview" and payload.entry and ref:
        key = digest(
            "entry:"
            + session
            + ":"
            + ref
            + ":"
            + acquisition["source"]
            + ":"
            + acquisition["campaign"]
        )
        await db.visitor_entries.update_one(
            {"_id": key},
            {"$setOnInsert": {"event": event, "expiresAt": expires}},
            upsert=True,
        )
        entry = (await db.visitor_entries.find_one({"_id": key})).get("event") == event
    target = host_label(payload.target)
    own = host_label(os.getenv("FRONTEND_URL", "https://tradingwithkaos.com"))
    target = (
        (
            "external:" + target
            if target and target != own
            else path_label(payload.target)
        )
        if payload.target
        else ""
    )
    doc = {
        "_id": event,
        "visitor": visitor,
        "session": session,
        "kind": payload.kind,
        "target": target,
        **acquisition,
        "path": path_label(payload.path),
        "referralClick": entry,
        "createdAt": stamp,
        "expiresAt": expires,
    }
    stored = await db.visitor_events.update_one(
        {"_id": event}, {"$setOnInsert": doc}, upsert=True
    )
    if stored.upserted_id and entry:
        daily = digest(
            "daily:"
            + ref
            + ":"
            + stamp.strftime("%Y-%m-%d")
            + ":"
            + acquisition["campaign"]
        )
        await db.affiliate_click_totals.update_one(
            {"_id": daily},
            {
                "$inc": {"clicks": 1},
                "$setOnInsert": {
                    "code": ref,
                    "day": stamp.strftime("%Y-%m-%d"),
                    "campaign": acquisition["campaign"],
                },
            },
            upsert=True,
        )
    return {"recorded": True}


async def acquisition_for(request):
    """Best-effort signup context. Telemetry must never prevent auth or billing."""
    headers = getattr(request, "headers", {}) or {}
    if not request or headers.get("dnt") == "1" or headers.get("sec-gpc") == "1":
        return None
    try:
        visitor = str(UUID(headers.get("x-kaos-visitor", "")))
        session = str(UUID(headers.get("x-kaos-session", "")))
        key = digest("session:" + visitor + ":" + session)
        row = await asyncio.wait_for(db.visitor_sessions.find_one({"_id": key}), 1.0)
        if not row:
            return None
        return {
            k: row.get(k)
            for k in (
                "source",
                "medium",
                "campaign",
                "referrerHost",
                "country",
                "path",
                "refCode",
            )
        }
    except Exception:
        return None


def event_scope(days, code=None, location=None, source=None):
    match = {"createdAt": {"$gte": now() - timedelta(days=days), "$lte": now()}}
    if code:
        match["refCode"] = code
    if location:
        match["country"] = location
    if source:
        match["source"] = source
    return match


async def report(days, code=None, location=None, source=None, offset=0, admin=False):
    await indexes()
    match = event_scope(days, code, location, source)
    count = lambda expression: {"$sum": {"$cond": [expression, 1, 0]}}
    facets = {
        "totals": [
            {
                "$group": {
                    "_id": None,
                    "pageviews": count({"$eq": ["$kind", "pageview"]}),
                    "navigationClicks": count({"$eq": ["$kind", "click"]}),
                    "referralClicks": count({"$eq": ["$referralClick", True]}),
                }
            }
        ],
        "visitors": [
            {"$match": {"kind": "pageview"}},
            {"$group": {"_id": "$visitor"}},
            {"$count": "count"},
        ],
        "sessions": [
            {"$match": {"kind": "pageview"}},
            {"$group": {"_id": "$session"}},
            {"$count": "count"},
        ],
        "countries": [
            {"$match": {"kind": "pageview"}},
            {
                "$group": {
                    "_id": {"country": "$country", "visitor": "$visitor"},
                    "pageviews": {"$sum": 1},
                }
            },
            {
                "$group": {
                    "_id": "$_id.country",
                    "visitors": {"$sum": 1},
                    "pageviews": {"$sum": "$pageviews"},
                }
            },
            {"$sort": {"visitors": -1, "_id": 1}},
            {"$limit": 30},
        ],
        "sources": [
            {
                "$group": {
                    "_id": {
                        "source": "$source",
                        "medium": "$medium",
                        "campaign": "$campaign",
                    },
                    "pageviews": count({"$eq": ["$kind", "pageview"]}),
                    "clicks": count({"$eq": ["$kind", "click"]}),
                    "referralClicks": count({"$eq": ["$referralClick", True]}),
                }
            },
            {"$sort": {"pageviews": -1, "_id.source": 1}},
            {"$limit": 20},
        ],
        "days": [
            {"$match": {"kind": "pageview"}},
            {
                "$group": {
                    "_id": {
                        "$dateToString": {
                            "format": "%Y-%m-%d",
                            "date": "$createdAt",
                            "timezone": "UTC",
                        }
                    },
                    "pageviews": {"$sum": 1},
                }
            },
            {"$sort": {"_id": 1}},
        ],
        "affiliates": [
            {"$match": {"referralClick": True}},
            {"$group": {"_id": "$refCode", "clicks": {"$sum": 1}}},
            {"$sort": {"clicks": -1, "_id": 1}},
            {"$limit": 20},
        ],
        "recent": [
            {"$sort": {"createdAt": -1, "_id": 1}},
            {"$skip": offset},
            {"$limit": 25},
            {"$project": {"_id": 0, "visitor": 0, "session": 0, "expiresAt": 0}},
        ],
    }
    rows = await db.visitor_events.aggregate(
        [{"$match": match}, {"$facet": facets}], maxTimeMS=4000
    ).to_list(1)
    data = rows[0] if rows else {key: [] for key in facets}
    summary = (data["totals"] or [{}])[0]
    summary.pop("_id", None)
    summary.setdefault("pageviews", 0)
    summary.setdefault("navigationClicks", 0)
    summary.setdefault("referralClicks", 0)
    summary.update(
        uniqueVisitors=(data["visitors"] or [{}])[0].get("count", 0),
        visits=(data["sessions"] or [{}])[0].get("count", 0),
    )
    users = {}
    if code:
        acc = await db.affiliate_accounts.find_one({"code": code}, {"userId": 1})
        users = {"referredByCode": code, "id": {"$ne": (acc or {}).get("userId")}}
    if location:
        users["analyticsAcquisition.country"] = location
    if source:
        users["analyticsAcquisition.source"] = source
    since = (now() - timedelta(days=days)).isoformat()
    acquired = {**users, "created_at": {"$gte": since, "$lte": now_iso()}}
    summary["newAccounts"] = await db.users.count_documents(acquired, maxTimeMS=2000)
    live = {
        "membership_expires_at": {"$gt": now_iso()},
        "stripe_subscription_id": {"$type": "string"},
    }
    summary["trialMembers"] = await db.users.count_documents(
        {**users, **live, "membership_status": "TRIAL"}, maxTimeMS=2000
    )
    summary["paidMembers"] = await db.users.count_documents(
        {**users, **live, "membership_status": "ACTIVE"}, maxTimeMS=2000
    )
    projection = {
        "_id": 0,
        "id": 1,
        "username": 1,
        "membership_plan": 1,
        "membership_status": 1,
        "membership_expires_at": 1,
        "created_at": 1,
        "referredByCode": 1,
        "analyticsAcquisition": 1,
    }
    members = (
        await db.users.find(acquired, projection)
        .sort([("created_at", -1), ("id", 1)])
        .skip(offset)
        .limit(25)
        .to_list(25)
    )
    for member in members:
        member["memberLabel"] = (
            member.pop("username", None) or "Member " + member["id"][-6:]
        )
        # Existing email/name fields are never selected for affiliate analytics.
    accounts = (
        await db.affiliate_accounts.find(
            {"code": {"$in": [a["_id"] for a in data["affiliates"]]}},
            {"_id": 0, "code": 1, "userId": 1},
        ).to_list(20)
        if admin
        else []
    )
    owners = {a["code"]: a["userId"] for a in accounts}
    return {
        "days": days,
        "summary": summary,
        "countries": data["countries"],
        "sources": data["sources"],
        "daily": data["days"],
        "affiliates": (
            [
                {
                    "code": a["_id"],
                    "clicks": a["clicks"],
                    "ownerUserId": owners.get(a["_id"]),
                }
                for a in data["affiliates"]
            ]
            if admin
            else []
        ),
        "recentEvents": data["recent"],
        "members": members,
        "offset": offset,
        "eventTotal": summary["pageviews"] + summary["navigationClicks"],
        "geoSource": source_info(),
        "retentionDays": RETENTION_DAYS,
        "memberCounts": "New accounts are in the selected period; trial and paid counts are current memberships across all signup dates.",
        "note": "Browser estimates, not people counts. Blockers, opt-outs and bots affect coverage. Country is approximate; unknown locations are not guessed. Detailed history starts with this release.",
    }


@router.get("/api/affiliate/analytics")
async def own_report(
    response: Response,
    days: int = Query(30, ge=1, le=90),
    offset: int = Query(0, ge=0, le=100000),
    location: str | None = Query(None, pattern="^[A-Z]{2}$"),
    source: str | None = Query(None, max_length=180),
    user: dict = Depends(get_current_user),
):
    from affiliate_access import require_paid_member

    require_paid_member(user)
    acc = await db.affiliate_accounts.find_one({"userId": user["id"]})
    if not acc or acc.get("status") != "active":
        raise HTTPException(403, "Active affiliate account required")
    response.headers["Cache-Control"] = "private, no-store"
    return await report(days, acc["code"], location, source, offset)


@router.get("/api/admin/analytics")
async def admin_report(
    response: Response,
    days: int = Query(30, ge=1, le=90),
    offset: int = Query(0, ge=0, le=100000),
    affiliate: str | None = Query(None, max_length=128),
    location: str | None = Query(None, pattern="^[A-Z]{2}$"),
    source: str | None = Query(None, max_length=180),
    user: dict = Depends(ADMIN),
):
    response.headers["Cache-Control"] = "private, no-store"
    return await report(days, affiliate, location, source, offset, True)
