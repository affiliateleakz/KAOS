import asyncio

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

import broker_vault


class Rows:
    def __init__(self, rows): self.rows = rows
    def find(self, q, proj):
        rows = self.rows
        class It:
            def __aiter__(self): self.i = iter(rows); return self
            async def __anext__(self):
                try: return next(self.i)
                except StopIteration: raise StopAsyncIteration
        return It()
    async def update_one(self, q, u):
        next(r for r in self.rows if r["_id"] == q["_id"]).update(u["$set"])


def test_rotation_reencrypts_under_new_key(monkeypatch):
    old, new = Fernet.generate_key().decode(), Fernet.generate_key().decode()
    rows = [{"_id": 1, "key_name_enc": Fernet(old).encrypt(b"name").decode(), "private_key_enc": Fernet(old).encrypt(b"secret").decode()}]
    monkeypatch.setenv("KAOS_BROKER_VAULT_KEY", new)
    monkeypatch.setenv("KAOS_BROKER_VAULT_PREVIOUS_KEYS", old)
    assert broker_vault.vault().decrypt(rows[0]["private_key_enc"].encode()) == b"secret"  # old data still readable
    assert asyncio.run(broker_vault.rotate_all(Rows(rows))) == 1
    monkeypatch.delenv("KAOS_BROKER_VAULT_PREVIOUS_KEYS")
    assert broker_vault.vault().decrypt(rows[0]["private_key_enc"].encode()) == b"secret"  # readable with new key only


def test_vault_missing_key_is_503(monkeypatch):
    monkeypatch.delenv("KAOS_BROKER_VAULT_KEY", raising=False)
    with pytest.raises(Exception) as e:
        broker_vault.vault()
    assert getattr(e.value, "status_code", None) == 503


def test_validation_errors_never_echo_submitted_private_key():
    from server import app
    from auth import get_current_user
    app.dependency_overrides[get_current_user] = lambda: {"id": "u", "email": "u@x"}
    try:
        secret = "SECRETKEYMATERIAL" * 300  # over max_length -> 422
        r = TestClient(app).put("/api/v1/broker-connections/coinbase", json={"key_name": "x", "private_key": secret})
        assert r.status_code == 422 and "SECRETKEYMATERIAL" not in r.text
    finally:
        app.dependency_overrides.clear()
