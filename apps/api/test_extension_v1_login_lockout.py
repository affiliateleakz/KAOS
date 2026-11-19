"""Extension v1 authentication respects the web login lockout counter."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
import routes_extension as ext
from models import LoginReq

def test_extension_login_uses_shared_lockout(monkeypatch):
    attempts=SimpleNamespace(find_one=AsyncMock(return_value={"count":5,"locked_until":"2099-01-01T00:00:00+00:00"}), update_one=AsyncMock(), delete_many=AsyncMock())
    users=SimpleNamespace(find_one=AsyncMock())
    monkeypatch.setattr(ext,"db",SimpleNamespace(login_attempts=attempts, users=users))
    request=SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"))
    req=LoginReq(email="member@example.com",password="incorrect")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(ext.v1_login(req,request))
    assert exc.value.status_code==429
    users.find_one.assert_not_awaited()

def test_extension_failed_login_increments_shared_counter(monkeypatch):
    attempts=SimpleNamespace(find_one=AsyncMock(return_value=None), update_one=AsyncMock(), delete_many=AsyncMock())
    users=SimpleNamespace(find_one=AsyncMock(return_value=None))
    monkeypatch.setattr(ext,"db",SimpleNamespace(login_attempts=attempts, users=users))
    request=SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"))
    req=LoginReq(email="member@example.com",password="incorrect")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(ext.v1_login(req,request))
    assert exc.value.status_code==401
    attempts.update_one.assert_awaited_once()
    assert attempts.update_one.await_args.args[0]["identifier"]=="127.0.0.1:member@example.com"
