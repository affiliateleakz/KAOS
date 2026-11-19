"""Legacy records must remain manageable without changing limits or other users."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from bson import ObjectId
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
import device_records
import routes_extension as ext
import routes_admin as admin
from auth import get_current_user


@pytest.mark.parametrize('mongo_id', [ObjectId(), 'old-native-device'])
def test_legacy_selector_round_trip_without_get_writes(mongo_id):
    row = {'_id': mongo_id, 'userId': 'owner', 'revoked': False}
    public = device_records.device_public(row)
    assert '_id' not in public
    assert row['_id'] == mongo_id
    query = device_records.device_query(public['id'], 'owner')
    assert query['_id'] == mongo_id
    assert query['userId'] == 'owner'
    assert '$or' in query  # May only target records without a KAOS id.


def test_legacy_member_can_list_and_revoke_own_device(monkeypatch):
    row = {'_id': ObjectId(), 'userId': 'owner', 'revoked': False, 'extensionVersion': '1.1.6'}
    update = AsyncMock(return_value=SimpleNamespace(matched_count=1))
    cursor = SimpleNamespace(to_list=AsyncMock(return_value=[row]))
    devices = SimpleNamespace(find=Mock(return_value=cursor), update_one=update)
    monkeypatch.setattr(ext, 'db', SimpleNamespace(devices=devices))
    app = FastAPI()
    app.include_router(ext.v1)
    app.dependency_overrides[get_current_user] = lambda: {'id': 'owner'}
    client = TestClient(app)
    listed = client.get('/api/v1/devices').json()
    devices.find.assert_called_once_with({'userId': 'owner'})
    update.assert_not_awaited()
    response = client.delete('/api/v1/devices/' + listed[0]['id'])
    assert response.status_code == 200
    assert update.await_args.args[0]['_id'] == row['_id']
    assert update.await_args.args[0]['userId'] == 'owner'


def test_missing_or_other_owners_device_is_not_reported_as_revoked(monkeypatch):
    update = AsyncMock(return_value=SimpleNamespace(matched_count=0))
    monkeypatch.setattr(ext, 'db', SimpleNamespace(devices=SimpleNamespace(update_one=update)))
    app = FastAPI()
    app.include_router(ext.v1)
    app.dependency_overrides[get_current_user] = lambda: {'id': 'alice'}
    client = TestClient(app)
    assert client.delete('/api/v1/devices/owners-device').status_code == 404
    assert update.await_args.args[0] == {'id': 'owners-device', 'userId': 'alice'}


def test_admin_revoke_requires_role_and_uses_legacy_selector(monkeypatch):
    mongo_id = ObjectId()
    selector = device_records.device_public({'_id': mongo_id})['id']
    update = AsyncMock(return_value=SimpleNamespace(matched_count=1))
    monkeypatch.setattr(admin, 'db', SimpleNamespace(devices=SimpleNamespace(update_one=update)))
    monkeypatch.setattr(admin, 'audit_log', AsyncMock())
    app = FastAPI()
    app.include_router(admin.router)
    client = TestClient(app)
    assert client.post(f'/api/admin/devices/{selector}/revoke').status_code == 401
    update.assert_not_awaited()
    app.dependency_overrides[get_current_user] = lambda: {'id': 'alice', 'role': 'user'}
    assert client.post(f'/api/admin/devices/{selector}/revoke').status_code == 403
    update.assert_not_awaited()
    app.dependency_overrides[admin.admin_dep] = lambda: {'id': 'owner', 'role': 'super_admin'}
    assert client.post(f'/api/admin/devices/{selector}/revoke').status_code == 200
    assert update.await_args.args[0]['_id'] == mongo_id
    assert 'userId' not in update.await_args.args[0]


def test_legacy_revoked_installation_cannot_reactivate(monkeypatch):
    row = {'_id': ObjectId(), 'userId': 'owner', 'installId': 'old-install', 'revoked': True}
    update = AsyncMock()
    monkeypatch.setattr(ext, 'db', SimpleNamespace(devices=SimpleNamespace(find_one=AsyncMock(return_value=row), update_one=update)))
    monkeypatch.setattr(ext, 'get_entitlements', AsyncMock(return_value={'botAccess': True, 'deviceLimit': 1}))
    from models import DeviceReq
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as err:
        asyncio.run(ext.register_device(DeviceReq(installId='old-install', deviceName='old'), SimpleNamespace(), {'id': 'owner'}))
    assert err.value.status_code == 403
    update.assert_not_awaited()


def test_legacy_existing_installation_preserves_its_registration(monkeypatch):
    row = {'_id': ObjectId(), 'userId': 'owner', 'installId': 'old-install', 'revoked': False}
    update = AsyncMock()
    count = AsyncMock()
    monkeypatch.setattr(ext, 'db', SimpleNamespace(devices=SimpleNamespace(find_one=AsyncMock(return_value=row), update_one=update, count_documents=count)))
    monkeypatch.setattr(ext, 'get_entitlements', AsyncMock(return_value={'botAccess': True, 'deviceLimit': 1}))
    from models import DeviceReq
    result = asyncio.run(ext.register_device(DeviceReq(installId='old-install', deviceName='old'), SimpleNamespace(), {'id': 'owner'}))
    assert result['id'].startswith('legacy-oid-')
    assert update.await_args.args[0]['_id'] == row['_id']
    assert update.await_args.args[0]['userId'] == 'owner'
    count.assert_not_awaited()


def test_revoke_legacy_device_frees_slot_without_touching_other_accounts(monkeypatch):
    import os
    from uuid import uuid4
    from motor.motor_asyncio import AsyncIOMotorClient
    from fastapi import HTTPException
    from models import DeviceReq

    async def scenario():
        client = AsyncIOMotorClient(os.environ['MONGO_URL'], serverSelectionTimeoutMS=3000)
        collection = client[os.environ['DB_NAME']]['legacy_devices_' + uuid4().hex]
        monkeypatch.setattr(ext, 'db', SimpleNamespace(devices=collection))
        monkeypatch.setattr(ext, 'get_entitlements', AsyncMock(return_value={'botAccess': True, 'deviceLimit': 1}))
        try:
            await collection.insert_many([
                {'userId': 'owner', 'installId': 'old', 'revoked': False},
                {'id': 'other-device', 'userId': 'alice', 'revoked': False},
            ])
            request = SimpleNamespace(client=None)
            req = DeviceReq(installId='current', deviceName='Current Chrome')
            with pytest.raises(HTTPException) as err:
                await ext.register_device(req, request, {'id': 'owner'})
            assert err.value.status_code == 403
            with pytest.raises(HTTPException) as forbidden:
                await ext.delete_device('other-device', {'id': 'owner'})
            assert forbidden.value.status_code == 404
            listed = await ext.list_devices({'id': 'owner'})
            await ext.delete_device(listed[0]['id'], {'id': 'owner'})
            registered = await ext.register_device(req, request, {'id': 'owner'})
            assert registered['installId'] == 'current'
            assert await collection.count_documents({'userId': 'owner', 'revoked': False}) == 1
            assert (await collection.find_one({'id': 'other-device'}))['revoked'] is False
            assert (await collection.find_one({'installId': 'old'}))['revoked'] is True
        finally:
            await collection.drop()
            client.close()
    asyncio.run(scenario())
