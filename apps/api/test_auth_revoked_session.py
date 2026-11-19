"""Previously issued JWTs and Google sessions respect account revocation."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
import auth

@pytest.mark.parametrize("status,revoked", [
    ("suspended",False), ("banned",False), ("active",True)
])
def test_existing_access_token_rejected_for_disabled_account(monkeypatch,status,revoked):
    user={"id":"u1","token_version":0,"account_status":status,
          "extension_access_revoked":revoked}
    monkeypatch.setattr(auth.jwt,"decode",lambda *a,**k:{"sub":"u1","ver":0,"type":"access"})
    monkeypatch.setattr(auth,"_secret",lambda:"test")
    monkeypatch.setattr(auth,"db",SimpleNamespace(users=SimpleNamespace(find_one=AsyncMock(return_value=user))))
    with pytest.raises(HTTPException) as err:
        asyncio.run(auth._user_from_token("previously-issued-token"))
    assert err.value.status_code==403

def test_google_session_rejected_after_account_ban(monkeypatch):
    monkeypatch.setattr(auth,"db",SimpleNamespace(
        sessions=SimpleNamespace(find_one=AsyncMock(return_value={"user_id":"u1"})),
        users=SimpleNamespace(find_one=AsyncMock(return_value={"id":"u1","account_status":"banned"}))))
    assert asyncio.run(auth._session_user("old-google-session")) is None
