import os
import logging
import hashlib
import secrets
from urllib.parse import urlsplit
from datetime import datetime, timezone, timedelta

import jwt
import bcrypt
from fastapi import Request, HTTPException, Depends

from db import db, clean

logger = logging.getLogger(__name__)
JWT_ALGORITHM = "HS256"

ROLE_RANK = {"user": 0, "moderator": 1, "admin": 2, "super_admin": 3}


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    if not hashed:
        return False
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def _secret() -> str:
    return os.environ["JWT_SECRET"]


def create_access_token(user_id: str, email: str, token_version: int = 0) -> str:
    payload = {"sub": user_id, "email": email, "ver": token_version,
               "exp": datetime.now(timezone.utc) + timedelta(minutes=15), "type": "access"}
    return jwt.encode(payload, _secret(), algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str, token_version: int = 0) -> str:
    payload = {"sub": user_id, "ver": token_version,
               "exp": datetime.now(timezone.utc) + timedelta(days=7), "type": "refresh"}
    return jwt.encode(payload, _secret(), algorithm=JWT_ALGORITHM)


def set_auth_cookies(response, access_token: str, refresh_token: str):
    response.set_cookie("access_token", access_token, httponly=True, secure=True,
                        samesite="none", max_age=900, path="/")
    response.set_cookie("refresh_token", refresh_token, httponly=True, secure=True,
                        samesite="none", max_age=604800, path="/")


def clear_auth_cookies(response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def gen_token() -> str:
    return secrets.token_urlsafe(32)


async def _user_from_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, _secret(), algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")
    user = await db.users.find_one({"id": payload["sub"]})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if payload.get("ver", 0) != user.get("token_version", 0):
        raise HTTPException(status_code=401, detail="Session expired")
    if user.get("account_status", "active") in ("suspended", "banned") or user.get("extension_access_revoked"):
        raise HTTPException(status_code=403, detail="Account access disabled")
    user = clean(user)
    user.pop("password_hash", None)
    return user


async def _session_user(token: str):
    """Emergent Google session token lookup."""
    sess = await db.sessions.find_one({"session_token": token})
    if not sess:
        return None
    exp = sess.get("expires_at")
    if isinstance(exp, str):
        exp = datetime.fromisoformat(exp)
    if exp and exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if exp and exp < datetime.now(timezone.utc):
        return None
    user = await db.users.find_one({"id": sess["user_id"]})
    if not user or user.get("account_status", "active") in ("suspended", "banned") or user.get("extension_access_revoked"):
        return None
    user = clean(user)
    user.pop("password_hash", None)
    return user


def _cookie_write_origin_allowed(request: Request) -> bool:
    """Require a trusted Origin (or Referer) for cookie-authenticated writes."""
    if request.method.upper() in ("GET", "HEAD", "OPTIONS", "TRACE"):
        return True
    raw = request.headers.get("origin") or request.headers.get("referer")
    if not raw or raw == "null":
        return False
    try:
        parsed = urlsplit(raw)
        candidate = f"{parsed.scheme}://{parsed.netloc}"
        if parsed.scheme not in ("https", "http") or not parsed.hostname:
            return False
        frontend = os.environ.get("FRONTEND_URL", "http://localhost:3000").rstrip("/")
        api_origin = os.environ.get("API_PUBLIC_ORIGIN", "").rstrip("/")
        allowed = {frontend}
        if api_origin:
            allowed.add(api_origin)
        if os.environ.get("KAOS_ENV", "").lower() != "production":
            allowed.add("http://localhost:3000")
        return candidate in allowed
    except (ValueError, AttributeError):
        return False


async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    session_token = request.cookies.get("session_token")
    bearer = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        bearer = auth_header[7:]

    # Explicit bearer credentials are not browser-ambient and do not need CSRF checks.
    if bearer:
        try:
            return await _user_from_token(bearer)
        except HTTPException:
            u = await _session_user(bearer)
            if u:
                return u
    # Cookies are ambient browser credentials; fail closed for unsafe writes.
    if (token or session_token) and not _cookie_write_origin_allowed(request):
        raise HTTPException(status_code=403, detail="Untrusted cookie request origin")
    for t in [token]:
        if t:
            try:
                return await _user_from_token(t)
            except HTTPException:
                pass
    if session_token:
        u = await _session_user(session_token)
        if u:
            return u
    raise HTTPException(status_code=401, detail="Not authenticated")


async def get_optional_user(request: Request):
    try:
        return await get_current_user(request)
    except HTTPException:
        return None


def require_role(min_role: str):
    async def _dep(user: dict = Depends(get_current_user)) -> dict:
        if ROLE_RANK.get(user.get("role", "user"), 0) < ROLE_RANK[min_role]:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return _dep
