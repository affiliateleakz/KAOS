"""Revoked extension devices cannot self-reactivate via device registration."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
import routes_extension as ext
from models import DeviceReq

def test_revoked_device_cannot_register_again(monkeypatch):
    devices=SimpleNamespace(find_one=AsyncMock(return_value={
        "id":"dev1","userId":"user1","installId":"install1","revoked":True}),
        update_one=AsyncMock())
    monkeypatch.setattr(ext,"db",SimpleNamespace(devices=devices))
    request=SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"))
    req=DeviceReq(installId="install1", deviceName="Windows", extensionVersion="1.7.11")
    with pytest.raises(HTTPException,match="Device access revoked") as err:
        asyncio.run(ext.register_device(req,request,user={"id":"user1"}))
    assert err.value.status_code==403
    devices.update_one.assert_not_awaited()
