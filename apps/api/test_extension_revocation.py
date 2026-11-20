"""Regression tests: revoked extension installations cannot re-register themselves."""
import asyncio
import os
from types import SimpleNamespace

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "kaos_test")

import pytest
from fastapi import HTTPException
import routes_extension as ext
from models import DeviceReq


def run(coro):
    return asyncio.run(coro)


class Devices:
    def __init__(self, doc):
        self.doc = doc
        self.updates = []

    async def find_one(self, query):
        if self.doc and all(
            (self.doc.get(k) == v if not isinstance(v, dict) else
             self.doc.get(k) != True if v == {"$ne": True} else False)
            for k, v in query.items()
        ):
            return dict(self.doc)
        return None

    async def update_one(self, query, update):
        self.updates.append((query, update))
        matched = await self.find_one(query)
        if matched:
            self.doc.update(update["$set"])
        return SimpleNamespace(matched_count=1 if matched else 0)


@pytest.fixture
def request():
    return SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"))


@pytest.fixture
def user():
    return {"id": "user-one"}


def test_revoked_installation_cannot_reactivate(monkeypatch, request, user):
    devices = Devices({"id": "dev-one", "userId": user["id"], "installId": "install-one", "revoked": True})
    monkeypatch.setattr(ext.db, "devices", devices)
    with pytest.raises(HTTPException) as error:
        run(ext.register_device(DeviceReq(installId="install-one"), request, user))
    assert error.value.status_code == 403
    assert devices.updates == []
    assert devices.doc["revoked"] is True


def test_active_installation_updates_without_revoked_reset(monkeypatch, request, user):
    devices = Devices({"id": "dev-one", "userId": user["id"], "installId": "install-one", "revoked": False})
    monkeypatch.setattr(ext.db, "devices", devices)
    out = run(ext.register_device(DeviceReq(installId="install-one", extensionVersion="1.2"), request, user))
    assert out["extensionVersion"] == "1.2"
    assert devices.doc["revoked"] is False
    assert "revoked" not in devices.updates[0][1]["$set"]
    assert devices.updates[0][0]["revoked"] == {"$ne": True}


def test_concurrent_revocation_fails_closed(monkeypatch, request, user):
    devices = Devices({"id": "dev-one", "userId": user["id"], "installId": "install-one", "revoked": False})
    async def revoked_during_update(query, update):
        devices.doc["revoked"] = True
        return SimpleNamespace(matched_count=0)
    devices.update_one = revoked_during_update
    monkeypatch.setattr(ext.db, "devices", devices)
    with pytest.raises(HTTPException) as error:
        run(ext.register_device(DeviceReq(installId="install-one"), request, user))
    assert error.value.status_code == 403
    assert devices.doc["revoked"] is True
