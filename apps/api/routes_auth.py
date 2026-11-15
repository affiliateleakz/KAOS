import os
import logging
from html import escape
from urllib.parse import urlparse
from datetime import datetime, timezone, timedelta

import httpx
from fastapi import APIRouter, Request, Response, HTTPException, Depends, BackgroundTasks

from db import db, new_id, now, now_iso, clean
from auth import (hash_password, verify_password, create_access_token, create_refresh_token,
                  set_auth_cookies, clear_auth_cookies, hash_token, gen_token,
                  get_current_user, _secret, JWT_ALGORITHM)
from services import public_user, notify, get_setting
from models import (RegisterReq, LoginReq, ForgotReq, ResetReq, VerifyReq, ProfileUpdate)
import jwt as pyjwt

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])

EMAIL_BASE_URL = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip().rstrip("/") or "https://integrations.emergentagent.com"
EMAIL_KEY = os.environ.get("EMERGENT_EMAIL_KEY", "")
EMAIL_FROM_NAME = os.environ.get("EMAIL_FROM_NAME") or "Trading Platform"

from login_policy import MAX_LOGIN_ATTEMPTS as MAX_ATTEMPTS, LOGIN_LOCK_MINUTES as LOCK_MINUTES


async def send_password_reset_email(to_email: str, token: str) -> bool:
    base = os.environ.get("FRONTEND_URL", "").rstrip("/")
    link = f"{base}/reset-password?token={token}"
    if not EMAIL_KEY or EMAIL_KEY.startswith("{") or not base.startswith("https://"):
        if urlparse(base).hostname in ("localhost", "127.0.0.1", "::1"):
            logger.warning("Email not configured; password reset link: %s", link)
        else:
            logger.error("Password reset email not configured")
        return False
    brand = escape(EMAIL_FROM_NAME)
    html = (f'<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial">'
            f'<p>We received a request to reset your {brand} password.</p>'
            f'<p><a href="{escape(link)}">Reset your password</a></p>'
            f'<p>This link expires in 1 hour and can be used once.</p></td></tr></table>')
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{EMAIL_BASE_URL}/api/v1/email/send",
                                     headers={"X-Email-Key": EMAIL_KEY},
                                     json={"to": [to_email], "subject": f"Reset your {EMAIL_FROM_NAME} password",
                                           "html": html, "from_name": EMAIL_FROM_NAME})
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Password reset email failed: {e}")
        return False


# Public account responses use an explicit allowlist. Mongo documents also contain
# authentication, verification, Stripe, licensing and administrative fields.
PUBLIC_ACCOUNT_FIELDS = frozenset({
    "id", "email", "name", "username", "role", "avatar", "bio",
    "email_verified", "auth_provider", "account_status", "onboarding_step",
    "affiliate_status", "affiliate_ref", "membership_status", "membership_plan",
    "membership_expires_at", "is_demo", "created_at", "updated_at", "requested_membership_plan",
})

def _user_public(user: dict) -> dict:
    safe = clean(dict(user))
    return {key: safe[key] for key in PUBLIC_ACCOUNT_FIELDS if key in safe}


async def _new_user_doc(email, name, username=None, password=None, provider="password",
                        google_id=None, avatar=None, verified=False):
    uid = new_id("user")
    return {
        "id": uid,
        "email": email.lower(),
        "name": name,
        "username": username or email.split("@")[0].lower() + uid[-4:],
        "password_hash": hash_password(password) if password else None,
        "role": "user",
        "email_verified": verified,
        "token_version": 0,
        "avatar": avatar,
        "bio": "",
        "auth_provider": provider,
        "google_id": google_id,
        "account_status": "active",
        "onboarding_step": 1,
        "affiliate_status": "NOT_STARTED",
        "affiliate_ref": None,
        "stripe_customer_id": None,
        "stripe_subscription_id": None,
        "membership_status": "EXPIRED",
        "membership_plan": None,
        "membership_expires_at": None,
        "extension_access_revoked": False,
        "license_id": new_id("lic"),
        "is_demo": False,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }


async def requested_plan(plan_id):
    if plan_id is None or plan_id == 'free': return 'free'
    if not isinstance(plan_id, str) or len(plan_id) > 64:
        raise HTTPException(400, 'Choose a valid membership')
    from routes_billing import get_plans
    if not any(plan.get('id') == plan_id and plan.get('enabled', True) is True for plan in await get_plans()):
        raise HTTPException(400, 'This membership is unavailable. Choose a current plan.')
    return plan_id


@router.post("/register")
async def register(req: RegisterReq, response: Response):
    email = req.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    selected_plan = await requested_plan(req.planId)
    doc = await _new_user_doc(email, req.name, req.username, req.password)
    # demo-mode email verification token returned in-app
    vtoken = gen_token()
    doc["verify_token"] = vtoken
    doc["referredByCode"] = (req.refCode or None)  # affiliate attribution (server-persisted)
    doc['requested_membership_plan'] = selected_plan  # Preference only; no paid access before verified payment.
    await db.users.insert_one(dict(doc))
    at = create_access_token(doc["id"], email, 0)
    rt = create_refresh_token(doc["id"], 0)
    set_auth_cookies(response, at, rt)
    out = _user_public(doc)
    # Registration must not let a user verify an unowned email address.
    # The demo token is available only in development; production requires a
    # separately authenticated email delivery/verification flow.
    if os.environ.get("KAOS_ENV", "production").lower() in ("development", "dev", "test"):
        out["verificationToken"] = vtoken
    return out


@router.post("/verify-email")
async def verify_email(req: VerifyReq, user: dict = Depends(get_current_user)):
    doc = await db.users.find_one({"id": user["id"]})
    if doc.get("email_verified"):
        return {"verified": True}
    if not req.token or req.token != doc.get("verify_token"):
        raise HTTPException(status_code=400, detail="Invalid verification token")
    await db.users.update_one({"id": user["id"]},
                              {"$set": {"email_verified": True, "onboarding_step": max(2, doc.get("onboarding_step", 1)), "updated_at": now_iso()}})
    return {"verified": True}


@router.post("/login")
async def login(req: LoginReq, request: Request, response: Response):
    email = req.email.lower()
    ip = request.client.host if request.client else "0.0.0.0"
    identifier = f"{ip}:{email}"
    attempt = await db.login_attempts.find_one({"identifier": identifier})
    if attempt and attempt.get("count", 0) >= MAX_ATTEMPTS:
        locked_until = attempt.get("locked_until")
        if locked_until and datetime.fromisoformat(locked_until) > now():
            raise HTTPException(status_code=429, detail="Too many attempts. Try again later.")

    user = await db.users.find_one({"email": email})
    if not user or not verify_password(req.password, user.get("password_hash") or ""):
        await db.login_attempts.update_one(
            {"identifier": identifier},
            {"$set": {"identifier": identifier, "email": email,
                      "locked_until": (now() + timedelta(minutes=LOCK_MINUTES)).isoformat()},
             "$inc": {"count": 1}}, upsert=True)
        raise HTTPException(status_code=401, detail="Invalid email or password")

    await db.login_attempts.delete_many({"identifier": identifier})
    tv = user.get("token_version", 0)
    at = create_access_token(user["id"], email, tv)
    rt = create_refresh_token(user["id"], tv)
    set_auth_cookies(response, at, rt)
    return _user_public(user)


@router.post("/logout")
async def logout(response: Response):
    clear_auth_cookies(response)
    response.delete_cookie("session_token", path="/")
    return {"ok": True}


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return _user_public(user)


@router.post("/refresh")
async def refresh(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
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
    if user.get("account_status", "active") != "active" or user.get("extension_access_revoked"):
        raise HTTPException(status_code=403, detail="Account access disabled")
    tv = user.get("token_version", 0)
    at = create_access_token(user["id"], user["email"], tv)
    rt = create_refresh_token(user["id"], tv)
    set_auth_cookies(response, at, rt)
    return {"ok": True}


@router.post("/forgot-password")
async def forgot_password(req: ForgotReq, background_tasks: BackgroundTasks):
    email = req.email.lower()
    generic = {"message": "If that email is registered, a reset link has been sent."}
    await db.password_reset_requests.insert_one({"email": email, "created_at": now()})
    recent = await db.password_reset_requests.count_documents({"email": email})
    if recent > 5:
        return generic
    user = await db.users.find_one({"email": email})
    if not user:
        return generic
    token = gen_token()
    await db.password_reset_tokens.insert_one({
        "token_hash": hash_token(token), "user_id": user["id"], "email": email,
        "expires_at": now() + timedelta(hours=1), "used": False})
    background_tasks.add_task(send_password_reset_email, user["email"], token)
    return generic


@router.post("/reset-password")
async def reset_password(req: ResetReq):
    h = hash_token(req.token)
    doc = await db.password_reset_tokens.find_one_and_update(
        {"token_hash": h, "used": False, "expires_at": {"$gt": now()}},
        {"$set": {"used": True}})
    if not doc:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    await db.users.update_one({"id": doc["user_id"]},
                              {"$set": {"password_hash": hash_password(req.password), "updated_at": now_iso()},
                               "$inc": {"token_version": 1}})
    await db.password_reset_tokens.delete_many({"user_id": doc["user_id"], "used": False})
    await db.login_attempts.delete_many({"email": doc["email"]})
    return {"ok": True}


# ---- Direct Google Identity Services credential sign-in ----
# This route is distinct from the legacy Emergent OAuth session integration.
# Audience must come from the server configuration, never from the caller.
async def _google_signin_identity(data: dict, registration: dict = None) -> dict:
    email = str(data.get("email") or "").lower().strip()
    google_id = str(data.get("sub") or "").strip()
    if not email or not google_id or data.get("email_verified") not in (True, "true", "True"):
        raise HTTPException(status_code=401, detail="Google email identity not verified")
    user = await db.users.find_one({"email": email})
    if user:
        if user.get("google_id") and user.get("google_id") != google_id:
            raise HTTPException(status_code=403, detail="Google account does not match linked identity")
        if user.get("account_status", "active") in ("suspended", "banned", "deleted") or user.get("extension_access_revoked"):
            raise HTTPException(status_code=403, detail="Account access disabled")
        await db.users.update_one({"id": user["id"]}, {"$set": {
            "google_id": google_id,
            "email_verified": True,
            "avatar": user.get("avatar") or data.get("picture"),
        }})
    else:
        doc = await _new_user_doc(email, data.get("name") or email, None, None,
                                  provider="google", google_id=google_id,
                                  avatar=data.get("picture"), verified=True)
        if registration:
            doc['requested_membership_plan'] = registration['planId']
            doc['referredByCode'] = registration.get('refCode')
        await db.users.insert_one(dict(doc))
        user = doc
    return user


@router.post("/google/credential")
async def google_credential(request: Request, response: Response):
    """Verify Google ID token; exchange it for first-party HttpOnly session cookies."""
    from google.oauth2 import id_token
    from google.auth.transport.requests import Request as GoogleRequest
    import asyncio

    client_id = os.environ.get("KAOS_GOOGLE_WEB_CLIENT_ID", "").strip()
    if not client_id:
        raise HTTPException(status_code=503, detail="Google sign-in is not configured")
    body = await request.json()
    credential = body.get("credential") if isinstance(body, dict) else None
    if not isinstance(credential, str) or not credential or len(credential) > 8192:
        raise HTTPException(status_code=400, detail="Google credential required")
    try:
        claims = await asyncio.to_thread(
            id_token.verify_oauth2_token, credential, GoogleRequest(), client_id
        )
    except Exception as exc:
        logger.warning("Google ID-token verification failed: %s", type(exc).__name__)
        raise HTTPException(status_code=401, detail="Invalid Google credential") from exc
    if claims.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
        raise HTTPException(status_code=401, detail="Invalid Google issuer")
    registration = None
    if body.get('planId') is not None:
        plan_id = await requested_plan(body.get('planId'))
        ref = body.get('refCode')
        if ref is not None and (not isinstance(ref, str) or len(ref) > 128):
            raise HTTPException(400, 'Invalid referral code')
        registration = {'planId': plan_id, 'refCode': ref}
    user = await _google_signin_identity(claims, registration) if registration else await _google_signin_identity(claims)
    tv = user.get("token_version", 0)
    set_auth_cookies(response, create_access_token(user["id"], user["email"], tv),
                     create_refresh_token(user["id"], tv))
    return _user_public(user)


# ---- Emergent Google OAuth ----
@router.post("/google/session")
async def google_session(request: Request, response: Response):
    session_id = request.headers.get("X-Session-ID")
    if not session_id:
        raise HTTPException(status_code=400, detail="Missing session id")
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get("https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
                             headers={"X-Session-ID": session_id})
    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid session")
    data = r.json()
    email = data["email"].lower()
    user = await db.users.find_one({"email": email})
    if not user:
        doc = await _new_user_doc(email, data.get("name", email), None, None,
                                  provider="google", google_id=data.get("id"),
                                  avatar=data.get("picture"), verified=True)
        await db.users.insert_one(dict(doc))
        user = doc
    else:
        await db.users.update_one({"id": user["id"]},
                                  {"$set": {"google_id": data.get("id"),
                                            "avatar": user.get("avatar") or data.get("picture"),
                                            "email_verified": True}})
    session_token = data["session_token"]
    await db.sessions.insert_one({"user_id": user["id"], "session_token": session_token,
                                  "expires_at": now() + timedelta(days=7), "created_at": now_iso()})
    response.set_cookie("session_token", session_token, httponly=True, secure=True,
                        samesite="none", max_age=604800, path="/")
    return _user_public(user)


# ---- Account / profile / privacy ----
@router.patch("/profile")
async def update_profile(req: ProfileUpdate, user: dict = Depends(get_current_user)):
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if "username" in updates:
        existing = await db.users.find_one({"username": updates["username"], "id": {"$ne": user["id"]}})
        if existing:
            raise HTTPException(status_code=400, detail="Username taken")
    updates["updated_at"] = now_iso()
    await db.users.update_one({"id": user["id"]}, {"$set": updates})
    doc = await db.users.find_one({"id": user["id"]})
    return _user_public(doc)


@router.get("/export")
async def export_data(user: dict = Depends(get_current_user)):
    strategies = await db.strategies.find({"ownerUserId": user["id"]}, {"_id": 0}).to_list(1000)
    devices = await db.devices.find({"userId": user["id"]}, {"_id": 0}).to_list(1000)
    return {"account": user, "strategies": strategies, "devices": devices, "exportedAt": now_iso()}


@router.delete("/account")
async def delete_account(response: Response, user: dict = Depends(get_current_user)):
    # defined deletion workflow: anonymize account, remove private data, keep attribution shells
    await db.strategies.delete_many({"ownerUserId": user["id"], "visibility": {"$ne": "PUBLIC"}})
    await db.devices.delete_many({"userId": user["id"]})
    await db.sessions.delete_many({"user_id": user["id"]})
    await db.users.update_one({"id": user["id"]}, {
        "$set": {"account_status": "deleted", "email": f"deleted_{user['id']}@deleted.local",
                 "name": "Deleted User", "password_hash": None, "membership_status": "EXPIRED",
                 "extension_access_revoked": True, "updated_at": now_iso()},
        "$inc": {"token_version": 1}})
    clear_auth_cookies(response)
    return {"deleted": True}
