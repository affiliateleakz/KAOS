"""Extension login and refresh must enforce account disablement."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
import routes_extension as ext

@pytest.mark.parametrize("status,revoked", [
    ("suspended",False),("banned",False),("active",True)
])
def test_extension_login_rejects_disabled_account(monkeypatch,status,revoked):
    user={"id":"u1","email":"test@example.com","password_hash":"hash",
          "account_status":status,"extension_access_revoked":revoked}
    monkeypatch.setattr(ext,"db",SimpleNamespace(users=SimpleNamespace(find_one=AsyncMock(return_value=user))))
    monkeypatch.setattr(ext,"verify_password",lambda plain,hashed:True)
    from models import LoginReq
    with pytest.raises(HTTPException) as error:
        asyncio.run(ext.v1_login(LoginReq(email="test@example.com",password="example password")))
    assert error.value.status_code==403
