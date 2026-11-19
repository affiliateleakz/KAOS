"""The extension session endpoint must remain device-authorized and entitlement-aware."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
import routes_extension as ext


def test_extension_me_returns_license_and_entitlements(monkeypatch):
    license_check = AsyncMock(return_value={"authorized": True, "reasons": []})
    entitlements = AsyncMock(return_value={"botAccess": True, "chartLimit": 1})
    monkeypatch.setattr(ext, "v1_license", license_check)
    monkeypatch.setattr(ext, "get_entitlements", entitlements)
    user = {"id": "u1", "username": "tester", "email": "tester@example.com"}
    request = SimpleNamespace(headers={"X-Device-Id": "install-1"})
    result = asyncio.run(ext.extension_me(request, user))
    assert result["license"]["authorized"] is True
    assert result["entitlements"]["chartLimit"] == 1
    assert result["user"]["id"] == "u1"
    license_check.assert_awaited_once_with(request, user)
    entitlements.assert_awaited_once_with(user)


def test_extension_me_fails_closed_if_device_is_not_authorized(monkeypatch):
    async def refused(*args):
        raise HTTPException(status_code=403, detail="Device not authorized")
    monkeypatch.setattr(ext, "v1_license", refused)
    entitlements = AsyncMock()
    monkeypatch.setattr(ext, "get_entitlements", entitlements)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(ext.extension_me(SimpleNamespace(headers={}), {"id": "u1"}))
    assert exc.value.status_code == 403
    entitlements.assert_not_awaited()
