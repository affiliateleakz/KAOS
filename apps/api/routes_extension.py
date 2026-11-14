"""Extension-facing v1 API + affiliate onboarding. Server is the license authority."""
from fastapi import APIRouter, HTTPException, Depends, Request, Response
from db import db, new_id, now, now_iso, clean
from auth import (verify_password, create_access_token, create_refresh_token,
                  get_current_user, _secret, JWT_ALGORITHM)
from services import compute_license, public_user, audit_log
from services_trading import get_entitlements
from models import LoginReq, DeviceReq, SyncPushReq, AffiliateSubmitReq
import jwt as pyjwt
import os
import httpx
from routes_auth import _google_signin_identity
from device_records import device_public, device_query, device_record_query

v1 = APIRouter(prefix="/api/v1", tags=["extension-v1"])
member = APIRouter(prefix="/api", tags=["member"])


# ---------- v1 Auth (bearer tokens in body for the extension) ----------
@v1.post("/auth/login")
async def v1_login(req: LoginReq, request: Request):
    # Share the web login's lockout authority: extension logins cannot bypass it.
    from datetime import datetime, timedelta
    from login_policy import MAX_LOGIN_ATTEMPTS as MAX_ATTEMPTS, LOGIN_LOCK_MINUTES as LOCK_MINUTES
    email = req.email.lower()
    ip = request.client.host if request.client else "0.0.0.0"
    identifier = f"{ip}:{email}"
    attempt = await db.login_attempts.find_one({"identifier": identifier})
    if attempt and attempt.get("count", 0) >= MAX_ATTEMPTS:
        until = attempt.get("locked_until")
        if until and datetime.fromisoformat(until) > now():
            raise HTTPException(status_code=429, detail="Too many attempts. Try again later.")
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(req.password, user.get("password_hash") or ""):
        await db.login_attempts.update_one(
            {"identifier": identifier},
            {"$set": {"identifier": identifier, "email": email,
                      "locked_until": (now() + timedelta(minutes=LOCK_MINUTES)).isoformat()},
             "$inc": {"count": 1}}, upsert=True)
        raise HTTPException(status_code=401, detail="Invalid credentials")
    await db.login_attempts.delete_many({"identifier": identifier})
    if user.get("account_status", "active") in ("suspended", "banned") or user.get("extension_access_revoked"):
        raise HTTPException(status_code=403, detail="Account access disabled")
    tv = user.get("token_version", 0)
    return {"accessToken": create_access_token(user["id"], user["email"], tv),
            "refreshToken": create_refresh_token(user["id"], tv),
            "user": {"id": user["id"], "username": user.get("username"), "email": user["email"]}}


@v1.post("/auth/refresh")
async def v1_refresh(request: Request):
    body = await request.json()
    token = body.get("refreshToken")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    try:
        payload = pyjwt.decode(token, _secret(), algorithms=[JWT_ALGORITHM])
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")
    user = await db.users.find_one({"id": payload["sub"]})
    if not user or payload.get("ver", 0) != user.get("token_version", 0):
        raise HTTPException(status_code=401, detail="Session expired")
    if user.get("account_status", "active") in ("suspended", "banned") or user.get("extension_access_revoked"):
        raise HTTPException(status_code=403, detail="Account access disabled")
    tv = user.get("token_version", 0)
    return {"accessToken": create_access_token(user["id"], user["email"], tv),
            "refreshToken": create_refresh_token(user["id"], tv)}


@v1.post("/auth/logout")
async def v1_logout(user: dict = Depends(get_current_user)):
    return {"ok": True}


@v1.get("/license/status")
async def v1_license(request: Request, user: dict = Depends(get_current_user)):
    device = None
    did = request.headers.get("X-Device-Id")
    if not did or not did.strip():
        raise HTTPException(status_code=400, detail="X-Device-Id required for extension license")
    if did:
        device = await db.devices.find_one({"installId": did, "userId": user["id"]})
        if not device:
            raise HTTPException(status_code=403, detail="Device is not registered")
        if device.get("revoked"):
            raise HTTPException(status_code=403, detail="Device access revoked")
        await db.devices.update_one({**device_record_query(device, user["id"]), "revoked": False},
                                    {"$set": {"lastActive": now_iso(),
                                              "lastIp": request.client.host if request.client else None}})
    selection = await db.member_broker_selections.find_one(
        {"user_id": user["id"]}, {"_id": 0, "broker": 1})
    selected = (selection or {}).get("broker")
    broker = "pocket_option" if selected in ("pocketoption", "pocket_option") else (selected or "unselected")
    return await compute_license(user, device, broker=broker)


@v1.get("/extension/me")
async def extension_me(request: Request, user: dict = Depends(get_current_user)):
    """Current extension session, with a device-checked license and server entitlements."""
    license_status = await v1_license(request, user)
    return {
        "user": {**public_user(user), "email": user.get("email")},
        "license": license_status,
        "entitlements": await get_entitlements(user),
    }


@v1.post("/extension/google/access-token")
async def extension_google_access_token(request: Request):
    """Exchange a Google-authenticated Chrome Identity access token for a KAOS JWT.

    Google verifies the access token; the audience is pinned to the extension's
    configured OAuth client ID, and email ownership is verified with Google.
    """
    expected_client = os.environ.get("KAOS_GOOGLE_EXTENSION_CLIENT_ID", "").strip()
    if not expected_client:
        raise HTTPException(status_code=503, detail="Extension Google sign-in not configured")
    payload = await request.json()
    token = payload.get("access_token") if isinstance(payload, dict) else None
    if not isinstance(token, str) or not token or len(token) > 4096:
        raise HTTPException(status_code=400, detail="Google access token required")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            info_response = await client.get("https://oauth2.googleapis.com/tokeninfo",
                                             params={"access_token": token})
            if info_response.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid Google access token")
            info = info_response.json()
            if info.get("aud") != expected_client and info.get("issued_to") != expected_client:
                raise HTTPException(status_code=401, detail="Unrecognized Google OAuth client")
            profile_response = await client.get(
                "https://openidconnect.googleapis.com/v1/userinfo",
                headers={"Authorization": "Bearer " + token})
            if profile_response.status_code != 200:
                raise HTTPException(status_code=401, detail="Google identity unavailable")
            profile = profile_response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="Google identity service unavailable") from exc
    user = await _google_signin_identity(profile)
    tv = user.get("token_version", 0)
    return {
        "accessToken": create_access_token(user["id"], user["email"], tv),
        "refreshToken": create_refresh_token(user["id"], tv),
        "user": {"id": user["id"], "username": user.get("username"), "email": user["email"]},
    }


# ---------- Devices ----------
@v1.post("/devices/register")
async def register_device(req: DeviceReq, request: Request, user: dict = Depends(get_current_user)):
    # Apply authorization before both existing-device re-registration and new registration.
    # Otherwise a suspended or revoked member could refresh an already enrolled device.
    entitlements = await get_entitlements(user)
    if not entitlements.get("botAccess") or user.get("extension_access_revoked"):
        raise HTTPException(status_code=403, detail="Bot access is not authorized")
    existing = await db.devices.find_one({"installId": req.installId, "userId": user["id"]})
    if existing:
        # A revoked device must not be able to restore its own authorization
        # simply by calling registration with the same install identifier.
        if existing.get("revoked"):
            raise HTTPException(status_code=403, detail="Device access revoked")
        await db.devices.update_one({**device_record_query(existing, user["id"]), "revoked": False},
                                    {"$set": {"extensionVersion": req.extensionVersion, "lastActive": now_iso()}})
        return device_public(await db.devices.find_one(device_record_query(existing, user["id"])))
    # The license and device registration must use the same plan authority.
    # Free members are limited to one device, not the old hardcoded three.
    limit = int(entitlements.get("deviceLimit") or 1)
    if limit < 1:
        raise HTTPException(status_code=403, detail="No devices permitted for this account")
    count = await db.devices.count_documents({"userId": user["id"], "revoked": False})
    if count >= limit:
        raise HTTPException(status_code=403, detail=f"Device limit reached ({limit})")
    doc = {"id": new_id("dev"), "userId": user["id"], "deviceName": req.deviceName,
           "installId": req.installId, "extensionVersion": req.extensionVersion,
           "lastIp": request.client.host if request.client else None,
           "revoked": False, "lastActive": now_iso(), "createdAt": now_iso()}
    await db.devices.insert_one(dict(doc))
    return clean(doc)


@v1.get("/devices")
async def list_devices(user: dict = Depends(get_current_user)):
    records = await db.devices.find({"userId": user["id"]}).to_list(100)
    return [device_public(record) for record in records]


@v1.delete("/devices/{did}")
async def delete_device(did: str, user: dict = Depends(get_current_user)):
    result = await db.devices.update_one(device_query(did, user["id"]), {"$set": {"revoked": True}})
    if result.matched_count != 1:
        raise HTTPException(status_code=404, detail="Device not found for this account")
    return {"revoked": True}


# ---------- Extension release ----------
@v1.get("/extension/latest")
async def extension_latest():
    rel = await db.extension_releases.find_one({"published": True}, {"_id": 0}, sort=[("createdAt", -1)])
    if not rel:
        return {"version": None}
    return rel


# ---------- v1 strategies (owner-scoped) ----------
@v1.get("/strategies")
async def v1_strategies(user: dict = Depends(get_current_user)):
    return await db.strategies.find({"ownerUserId": user["id"]}, {"_id": 0}).to_list(500)


@v1.get("/community/strategies")
async def v1_community():
    return await db.strategies.find({"published": True, "visibility": "PUBLIC"}, {"_id": 0}).sort("likesCount", -1).to_list(100)


# ---------- Cloud sync (conflict-safe) ----------
@v1.get("/sync")
async def sync_pull(since: str = None, user: dict = Depends(get_current_user)):
    q = {"ownerUserId": user["id"]}
    if since:
        q["updatedAt"] = {"$gt": since}
    docs = await db.strategies.find(q, {"_id": 0}).to_list(1000)
    return {"serverTime": now_iso(), "strategies": docs}


# Fields derived from publication, moderation or engagement are server-owned.
# The cloud sync API may edit strategy definitions, not grant community status.
SYNC_SERVER_FIELDS = frozenset({
    "_id", "published", "verified", "likesCount", "createdAt",
    "publishedAt", "verifiedAt", "moderationStatus", "featured",
    "approved", "approvalStatus", "likes", "forksCount", "downloadsCount",
})

@v1.post("/sync")
async def sync_push(req: SyncPushReq, user: dict = Depends(get_current_user)):
    applied, conflicts = [], []
    for incoming in req.strategies:
        if not isinstance(incoming, dict) or SYNC_SERVER_FIELDS.intersection(incoming):
            raise HTTPException(status_code=422, detail="Server-managed strategy fields cannot be synced")
        incoming = dict(incoming)
        sid = incoming.get("id")
        if sid is not None and (not isinstance(sid, str) or not sid.strip() or len(sid) > 128):
            raise HTTPException(status_code=422, detail="Strategy id must be a nonempty string")
        if "ownerUserId" in incoming and incoming["ownerUserId"] != user["id"]:
            raise HTTPException(status_code=403, detail="Cannot change strategy ownership")
        existing = await db.strategies.find_one({"id": sid, "ownerUserId": user["id"]}) if sid else None
        if not existing:
            incoming["ownerUserId"] = user["id"]
            incoming.setdefault("id", new_id("strat"))
            incoming.setdefault("version", 1)
            incoming.setdefault("visibility", "PRIVATE")
            incoming["updatedAt"] = now_iso()
            await db.strategies.insert_one(dict(incoming))
            applied.append(incoming["id"])
        else:
            if incoming.get("updatedAt", "") < existing.get("updatedAt", ""):
                conflicts.append({"id": sid, "reason": "server_newer", "server": clean(existing)})
            else:
                incoming["updatedAt"] = now_iso()
                await db.strategies.update_one({"id": sid, "ownerUserId": user["id"]}, {"$set": {k: v for k, v in incoming.items() if k not in ("id", "ownerUserId", "_id")}})
                applied.append(sid)
    return {"applied": applied, "conflicts": conflicts, "serverTime": now_iso()}


# ---------- Member affiliate onboarding (pluggable verifier) ----------
@member.get("/affiliate/config")
async def affiliate_config():
    from services import get_setting
    cfg = await get_setting("affiliate", {})
    return {
        "affiliateUrl": cfg.get("affiliateUrl") or None,
        "programName": cfg.get("programName", "Optional Pocket Option Referral"),
        "verificationMethod": cfg.get("verificationMethod", "manual"),
        "referralRequired": False,
        "instructions": "Using a KAOS referral link is optional and is never required for membership or trading access.",
    }


@member.post("/affiliate/submit")
async def affiliate_submit(req: AffiliateSubmitReq, user: dict = Depends(get_current_user)):
    ref = {"id": new_id("aff"), "userId": user["id"], "poUid": req.poUid,
           "email": req.email, "note": req.note, "status": "PENDING",
           "verifier": "manual", "createdAt": now_iso(), "updatedAt": now_iso()}
    await db.affiliate_referrals.update_one({"userId": user["id"]}, {"$set": ref}, upsert=True)
    await db.affiliate_verifications.insert_one({"id": new_id("affv"), "userId": user["id"],
                                                 "poUid": req.poUid, "status": "MANUAL_REVIEW", "createdAt": now_iso()})
    await db.users.update_one({"id": user["id"]},
                              {"$set": {"affiliate_status": "PENDING", "affiliate_ref": req.poUid,
                                        "onboarding_step": max(4, user.get("onboarding_step", 1)), "updated_at": now_iso()}})
    return {"affiliateStatus": "PENDING"}


@member.get("/affiliate/status")
async def affiliate_status(user: dict = Depends(get_current_user)):
    ref = await db.affiliate_referrals.find_one({"userId": user["id"]}, {"_id": 0})
    return {"affiliateStatus": user.get("affiliate_status", "NOT_STARTED"), "referral": ref}


# ---------- Member dashboard aggregate ----------
@member.get("/dashboard")
async def dashboard(user: dict = Depends(get_current_user)):
    lic = await compute_license(user)
    my = await db.strategies.count_documents({"ownerUserId": user["id"]})
    published = await db.strategies.count_documents({"ownerUserId": user["id"], "published": True})
    saved = await db.strategy_saves.count_documents({"userId": user["id"]})
    devices = await db.devices.find({"userId": user["id"], "revoked": False}, {"_id": 0}).to_list(50)
    notifs = await db.notifications.find({"userId": user["id"]}, {"_id": 0}).sort("createdAt", -1).to_list(10)
    rel = await db.extension_releases.find_one({"published": True}, {"_id": 0}, sort=[("createdAt", -1)])
    return {
        "license": lic,
        "membershipStatus": user.get("membership_status"),
        "membershipPlan": user.get("membership_plan"),
        "membershipExpiresAt": user.get("membership_expires_at"),
        "affiliateStatus": user.get("affiliate_status"),
        "onboardingStep": user.get("onboarding_step", 1),
        "emailVerified": user.get("email_verified"),
        "counts": {"myStrategies": my, "published": published, "saved": saved, "devices": len(devices)},
        "devices": devices,
        "recentActivity": notifs,
        "latestExtension": rel,
    }
