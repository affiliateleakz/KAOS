"""Device self-service must remain owner-scoped through the validation gate."""
from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
import routes_extension as ext
from auth import get_current_user


def test_device_revocation_requires_authenticated_owner(monkeypatch):
    update = AsyncMock()
    monkeypatch.setattr(ext, 'db', SimpleNamespace(devices=SimpleNamespace(update_one=update)))
    app = FastAPI()
    app.include_router(ext.v1)
    client = TestClient(app)
    assert client.delete('/api/v1/devices/other-device').status_code == 401
    update.assert_not_awaited()
    app.dependency_overrides[get_current_user] = lambda: {'id': 'signed-in-owner'}
    assert client.delete('/api/v1/devices/other-device').status_code == 200
    update.assert_awaited_once_with(
        {'id': 'other-device', 'userId': 'signed-in-owner'}, {'$set': {'revoked': True}})
