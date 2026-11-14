import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from models import DeviceReq
from device_policy import device_entitlements, unlimited_devices
import routes_extension as ext
import services_trading as trading


@pytest.mark.parametrize('role', ['admin', 'super_admin'])
def test_admin_device_entitlements_are_explicitly_unlimited(role):
    user = {'role': role}
    ent = asyncio.run(trading.get_entitlements(user))
    assert ent['devicesUnlimited'] is True
    assert ent['deviceLimit'] is None
    assert ent['chartLimit'] == 1  # Device capability does not upgrade other plan features.


@pytest.mark.parametrize('role', ['user', 'moderator', 'owner', None])
def test_other_roles_keep_plan_device_limits(role):
    ent = device_entitlements({'role': role}, {'deviceLimit': 3, 'devicesUnlimited': True})
    assert ent == {'deviceLimit': 3, 'devicesUnlimited': False}


@pytest.mark.parametrize('role', ['admin', 'super_admin'])
def test_admin_can_register_beyond_membership_device_capacity(monkeypatch, role):
    devices = SimpleNamespace(find_one=AsyncMock(return_value=None),
        count_documents=AsyncMock(return_value=9999), insert_one=AsyncMock())
    monkeypatch.setattr(ext, 'db', SimpleNamespace(devices=devices))
    monkeypatch.setattr(ext, 'get_entitlements', AsyncMock(return_value={'botAccess': True, 'deviceLimit': 1}))
    result = asyncio.run(ext.register_device(
        DeviceReq(installId='new-install', deviceName='New Chrome'),
        SimpleNamespace(client=None), {'id': 'admin-id', 'role': role}))
    assert result['userId'] == 'admin-id'
    assert result['installId'] == 'new-install'
    devices.insert_one.assert_awaited_once()
    devices.count_documents.assert_not_awaited()


def test_member_cannot_bypass_limit_with_unlimited_plan_flag(monkeypatch):
    devices = SimpleNamespace(find_one=AsyncMock(return_value=None),
        count_documents=AsyncMock(return_value=1), insert_one=AsyncMock())
    monkeypatch.setattr(ext, 'db', SimpleNamespace(devices=devices))
    monkeypatch.setattr(ext, 'get_entitlements', AsyncMock(return_value={'botAccess': True, 'deviceLimit': 1, 'devicesUnlimited': True}))
    with pytest.raises(HTTPException) as err:
        asyncio.run(ext.register_device(DeviceReq(installId='new', deviceName='Chrome'),
            SimpleNamespace(client=None), {'id': 'member', 'role': 'user', 'username': 'owner'}))
    assert err.value.status_code == 403
    devices.insert_one.assert_not_awaited()


@pytest.mark.parametrize('status,revoked', [('suspended', False), ('banned', False), ('active', True)])
def test_disabled_admin_is_not_unlimited_or_allowed_to_register(monkeypatch, status, revoked):
    user = {'id': 'admin-id', 'role': 'super_admin', 'account_status': status, 'extension_access_revoked': revoked}
    assert not unlimited_devices(user)
    devices = SimpleNamespace(find_one=AsyncMock(), insert_one=AsyncMock())
    monkeypatch.setattr(ext, 'db', SimpleNamespace(devices=devices))
    ent = asyncio.run(trading.get_entitlements(user))
    monkeypatch.setattr(ext, 'get_entitlements', AsyncMock(return_value=ent))
    with pytest.raises(HTTPException) as err:
        asyncio.run(ext.register_device(DeviceReq(installId='new', deviceName='Chrome'), SimpleNamespace(client=None), user))
    assert err.value.status_code == 403
    devices.find_one.assert_not_awaited()
    devices.insert_one.assert_not_awaited()


def test_admin_cannot_reactivate_revoked_installation(monkeypatch):
    devices = SimpleNamespace(find_one=AsyncMock(return_value={'id': 'dev1', 'revoked': True}), update_one=AsyncMock(), insert_one=AsyncMock())
    monkeypatch.setattr(ext, 'db', SimpleNamespace(devices=devices))
    monkeypatch.setattr(ext, 'get_entitlements', AsyncMock(return_value={'botAccess': True, 'deviceLimit': None, 'devicesUnlimited': True}))
    with pytest.raises(HTTPException) as err:
        asyncio.run(ext.register_device(DeviceReq(installId='revoked', deviceName='Chrome'),
            SimpleNamespace(client=None), {'id': 'admin-id', 'role': 'super_admin'}))
    assert err.value.status_code == 403
    devices.update_one.assert_not_awaited()
    devices.insert_one.assert_not_awaited()
