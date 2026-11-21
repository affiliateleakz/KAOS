"""Extension-facing v1 API + affiliate onboarding. Server is the license authority."""
from fastapi import APIRouter, HTTPException, Depends, Request, Response
from db import db, new_id, now, now_iso, clean
from auth import (verify_password, create_access_token, create_refresh_token,
                  get_current_user, _secret, JWT_ALGORITHM)
from services import compute_license, public_user, audit_log
from models import LoginReq, DeviceReq, SyncPushReq, AffiliateSubmitReq
import jwt as pyjwt

v1 = APIRouter(prefix="/api/v1", tags=["extension-v1"])
member = APIRouter(prefix="/api", tags=["member"])


# ---------- v1 Auth (bearer tokens in body for the extension) ----------
@v1.post("/auth/login")
async def v1_login(req: LoginReq):
    user = await db.users.find_one({"email": req.email.lower()})
    if not user or not verify_password(req.password, user.get("password_hash") or ""):
        raise HTTPException(status_code=401, detail="Invalid credentials")
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
    if did:
        device = await db.devices.find_one({"installId": did, "userId": user["id"]})
        if device:
            await db.devices.update_one({"id": device["id"]},
                                        {"$set": {"lastActive": now_iso(),
                                                  "lastIp": request.client.host if request.client else None}})
    return await compute_license(user, device)


# ---------- Devices ----------
@v1.post("/devices/register")
async def register_device(req: DeviceReq, request: Request, user: dict = Depends(get_current_user)):
    from routes_billing import get_plans
    existing = await db.devices.find_one({"installId": req.installId, "userId": user["id"]})
    if existing:
        # Device revocation is an owner/admin decision; a revoked device cannot
        # self-reactivate by calling the registration endpoint.
        if existing.get("revoked"):
            raise HTTPException(status_code=403, detail="Device revoked")
        updated = await db.devices.update_one(
            {"id": existing["id"], "userId": user["id"], "revoked": {"$ne": True}},
            {"$set": {"extensionVersion": req.extensionVersion, "lastActive": now_iso()}},
        )
        if updated.matched_count != 1:
            raise HTTPException(status_code=403, detail="Device revoked")
        current = await db.devices.find_one({"id": existing["id"], "userId": user["id"]})
        if not current or current.get("revoked"):
            raise HTTPException(status_code=403, detail="Device revoked")
        return clean(current)
    plans = await get_plans()
    plan = next((p for p in plans if p["id"] == user.get("membership_plan")), None)
    limit = plan["deviceLimit"] if plan else 3
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
    return await db.devices.find({"userId": user["id"]}, {"_id": 0}).to_list(100)


@v1.delete("/devices/{did}")
async def delete_device(did: str, user: dict = Depends(get_current_user)):
    await db.devices.update_one({"id": did, "userId": user["id"]}, {"$set": {"revoked": True}})
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


@v1.post("/sync")
async def sync_push(req: SyncPushReq, user: dict = Depends(get_current_user)):
    applied, conflicts = [], []
    for incoming in req.strategies:
        sid = incoming.get("id")
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
                await db.strategies.update_one({"id": sid}, {"$set": {k: v for k, v in incoming.items() if k not in ("id", "ownerUserId")}})
                applied.append(sid)
    return {"applied": applied, "conflicts": conflicts, "serverTime": now_iso()}


# ---------- Member affiliate onboarding (pluggable verifier) ----------
@member.get("/affiliate/config")
async def affiliate_config():
    from services import get_setting
    cfg = await get_setting("affiliate", {})
    return {
        "affiliateUrl": cfg.get("affiliateUrl", "https://pocketoption.com/?ref=DEMO_AFFILIATE"),
        "programName": cfg.get("programName", "Pocket Option Partners"),
        "verificationMethod": cfg.get("verificationMethod", "manual"),
        "instructions": cfg.get("instructions",
                                "Create your Pocket Option account using our link, then submit your Pocket Option UID for verification."),
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
