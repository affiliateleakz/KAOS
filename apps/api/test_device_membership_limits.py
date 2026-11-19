"""Device registration must respect the same feature entitlements as the bot."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
import routes_extension as ext

def run(coro):
    return asyncio.run(coro)

def request():
    return SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"))

def device_req():
    return SimpleNamespace(installId="install-b", extensionVersion="1.7.11", deviceName="Test")

def test_free_member_cannot_register_second_device(monkeypatch):
    fake=SimpleNamespace(devices=SimpleNamespace(
        find_one=AsyncMock(return_value=None), count_documents=AsyncMock(return_value=1),
        insert_one=AsyncMock()))
    monkeypatch.setattr(ext,"db",fake)
    monkeypatch.setattr(ext,"get_entitlements",
                        AsyncMock(return_value={"botAccess":True,"deviceLimit":1}))
    with pytest.raises(HTTPException) as raised:
        run(ext.register_device(device_req(),request(),{"id":"u1","membership_status":"EXPIRED"}))
    assert raised.value.status_code==403
    fake.devices.insert_one.assert_not_awaited()

def test_revoked_entitlement_blocks_new_device(monkeypatch):
    fake=SimpleNamespace(devices=SimpleNamespace(
        find_one=AsyncMock(return_value=None),count_documents=AsyncMock(return_value=0),
        insert_one=AsyncMock()))
    monkeypatch.setattr(ext,"db",fake)
    monkeypatch.setattr(ext,"get_entitlements",
                        AsyncMock(return_value={"botAccess":False,"deviceLimit":1}))
    with pytest.raises(HTTPException) as raised:
        run(ext.register_device(device_req(),request(),{"id":"u1"}))
    assert raised.value.status_code==403
    fake.devices.insert_one.assert_not_awaited()

def test_existing_device_cannot_bypass_revoked_account(monkeypatch):
    existing={"id":"dev1","installId":"install-b","userId":"u1","revoked":False}
    fake=SimpleNamespace(devices=SimpleNamespace(
        find_one=AsyncMock(return_value=existing), update_one=AsyncMock(),
        count_documents=AsyncMock()))
    monkeypatch.setattr(ext,"db",fake)
    monkeypatch.setattr(ext,"get_entitlements",
                        AsyncMock(return_value={"botAccess":True,"deviceLimit":3}))
    with pytest.raises(HTTPException) as raised:
        run(ext.register_device(device_req(),request(),{
            "id":"u1","extension_access_revoked":True}))
    assert raised.value.status_code==403
    fake.devices.update_one.assert_not_awaited()

def test_existing_device_cannot_bypass_disabled_bot_entitlement(monkeypatch):
    existing={"id":"dev1","installId":"install-b","userId":"u1","revoked":False}
    fake=SimpleNamespace(devices=SimpleNamespace(
        find_one=AsyncMock(return_value=existing),update_one=AsyncMock()))
    monkeypatch.setattr(ext,"db",fake)
    monkeypatch.setattr(ext,"get_entitlements",
                        AsyncMock(return_value={"botAccess":False,"deviceLimit":1}))
    with pytest.raises(HTTPException) as raised:
        run(ext.register_device(device_req(),request(),{"id":"u1"}))
    assert raised.value.status_code==403
    fake.devices.update_one.assert_not_awaited()
