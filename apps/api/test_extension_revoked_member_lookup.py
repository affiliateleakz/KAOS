"""Revoked extension devices cannot obtain member licensing."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
import routes_botsync as bot

def test_revoked_device_rejected_before_broker_or_entitlement_lookup(monkeypatch):
    devices=SimpleNamespace(find_one=AsyncMock(return_value={"id":"device1","revoked":True}))
    selections=SimpleNamespace(find_one=AsyncMock())
    monkeypatch.setattr(bot,"db",SimpleNamespace(devices=devices,member_broker_selections=selections))
    request=SimpleNamespace(headers={"X-Device-Id":"revoked-install"})
    with pytest.raises(HTTPException) as exc:
        asyncio.run(bot.ext_me(request,{"id":"u1","email":"test@example.com"}))
    assert exc.value.status_code==403
    selections.find_one.assert_not_awaited()
