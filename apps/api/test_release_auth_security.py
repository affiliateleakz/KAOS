"""Regression tests for production user disclosure, login and broker authentication."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

import routes_auth
import routes_trading
import routes_extension


def test_account_response_never_discloses_database_secrets():
    user = {
        "id": "user_1", "email": "test@example.com", "membership_plan": "PRO",
        "password_hash": "$bcrypt", "verify_token": "verification-secret",
        "token_version": 8, "stripe_customer_id": "cus_private",
        "stripe_subscription_id": "sub_private", "license_id": "lic_private",
        "google_id": "google-sub", "extension_access_revoked": False,
        "reset_token": "private",
    }
    public = routes_auth._user_public(user)
    assert public["id"] == user["id"]
    assert public["email"] == user["email"]
    assert public["membership_plan"] == "PRO"
    for field in ("password_hash", "verify_token", "token_version",
                  "stripe_customer_id", "stripe_subscription_id",
                  "license_id", "google_id", "reset_token"):
        assert field not in public


def test_me_uses_account_allowlist():
    user = {"id": "u1", "email": "a@example.com", "password_hash": "hidden"}
    assert asyncio.run(routes_auth.me(user)) == {"id": "u1", "email": "a@example.com"}


@pytest.mark.parametrize("device_id,device,expected", [
    (None, None, 403),
    ("", None, 403),
    ("device-1", None, 403),
    ("device-1", {"id": "d", "revoked": True}, 403),
])
def test_trading_requires_registered_nonrevoked_device(monkeypatch, device_id, device, expected):
    query = AsyncMock(return_value=device)
    monkeypatch.setattr(routes_trading, "db",
                        SimpleNamespace(devices=SimpleNamespace(find_one=query)))
    request = SimpleNamespace(headers={"X-Device-Id": device_id} if device_id is not None else {})
    with pytest.raises(HTTPException) as exc:
        asyncio.run(routes_trading._require_authorized(request, {"id": "u1"}))
    assert exc.value.status_code == expected


def test_google_identity_rejects_unverified_email():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(routes_auth._google_signin_identity({
            "email": "test@example.com", "sub": "google123", "email_verified": False,
        }))
    assert exc.value.status_code == 401


def test_google_identity_rejects_changed_google_subject(monkeypatch):
    user = {"id": "u1", "email": "test@example.com", "google_id": "original"}
    monkeypatch.setattr(routes_auth, "db", SimpleNamespace(
        users=SimpleNamespace(find_one=AsyncMock(return_value=user))))
    with pytest.raises(HTTPException) as exc:
        asyncio.run(routes_auth._google_signin_identity({
            "email": "test@example.com", "sub": "different", "email_verified": True,
        }))
    assert exc.value.status_code == 403


def test_extension_google_route_requires_config(monkeypatch):
    monkeypatch.delenv("KAOS_GOOGLE_EXTENSION_CLIENT_ID", raising=False)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(routes_extension.extension_google_access_token(
            SimpleNamespace(json=AsyncMock(return_value={"access_token": "valid-looking"}))))
    assert exc.value.status_code == 503
