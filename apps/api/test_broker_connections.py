import os
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "kaos_test")
os.environ.setdefault("JWT_SECRET", "test-only-jwt-secret")

import asyncio

import pytest
from fastapi import HTTPException

import routes_broker_connections as rbc


def run(coro):
    return asyncio.run(coro)


class FakeCursor:
    def __init__(self, rows):
        self.rows = rows

    async def to_list(self, limit):
        return self.rows[:limit]


class FakeConnections:
    def __init__(self, rows=None):
        self.rows = list(rows or [])
        self.upsert = None
        self.deleted = 0

    def find(self, query, projection=None):
        rows = [r for r in self.rows if all(r.get(k) == v for k, v in query.items())]
        return FakeCursor(rows)

    async def update_one(self, query, update, upsert=False):
        self.upsert = (query, update)
        for row in self.rows:
            if all(row.get(k) == v for k, v in query.items()):
                row.update(update.get("$set", {}))
                return
        self.rows.append({**query, **update.get("$set", {})})

    async def delete_one(self, query):
        before = len(self.rows)
        self.rows = [r for r in self.rows if not all(r.get(k) == v for k, v in query.items())]
        self.deleted = before - len(self.rows)
        result = type("DeleteResult", (), {"deleted_count": self.deleted})()
        return result


class FakeDb:
    def __init__(self, connections=None):
        self.broker_connections = connections or FakeConnections()


class FakeFernet:
    def encrypt(self, value):
        return b"enc:" + value


USER = {"id": "user_1", "account_status": "active", "extension_access_revoked": False}


@pytest.fixture(autouse=True)
def no_audit(monkeypatch):
    async def audit(*args, **kwargs):
        return None
    monkeypatch.setattr(rbc, "audit_log", audit)


def test_list_never_discloses_stored_secrets(monkeypatch):
    db = FakeDb(FakeConnections([{
        "user_id": "user_1", "broker": "coinbase", "verified": True, "saved": True,
        "key_name_enc": "enc:organizations/abc/apiKeys/secret-name",
        "private_key_enc": "enc:-----BEGIN PRIVATE KEY-----",
        "key_hint": "…abcd", "updated_at": "2026-01-01T00:00:00Z",
    }]))
    monkeypatch.setattr(rbc, "db", db)
    out = run(rbc.list_connections(user=USER))
    blob = repr(out)
    assert "BEGIN PRIVATE KEY" not in blob and "apiKeys/secret-name" not in blob
    assert out["connections"][0]["key_hint"] == "…abcd"
    assert out["connections"][0]["verified"] is True


def test_save_refuses_to_store_when_vault_is_unconfigured(monkeypatch):
    db = FakeDb()
    monkeypatch.setattr(rbc, "db", db)

    def no_vault():
        raise HTTPException(503, "Broker vault not configured on this server")
    monkeypatch.setattr(rbc, "vault", no_vault)

    async def must_not_verify(*args, **kwargs):
        raise AssertionError("credentials must not be verified or stored without a vault")
    monkeypatch.setattr(rbc, "_verify_coinbase", must_not_verify)

    with pytest.raises(HTTPException) as err:
        run(rbc.save_coinbase(
            rbc.CoinbaseCredentials(key_name="organizations/abc/apiKeys/name", private_key="k" * 40),
            user=USER))
    assert err.value.status_code == 503
    assert db.broker_connections.upsert is None


def test_save_encrypts_credentials_and_returns_only_a_hint(monkeypatch):
    db = FakeDb()
    monkeypatch.setattr(rbc, "db", db)
    monkeypatch.setattr(rbc, "vault", lambda: FakeFernet())
    verified = {}

    async def verify(key_name, private_key):
        verified["key_name"] = key_name
        verified["private_key"] = private_key
    monkeypatch.setattr(rbc, "_verify_coinbase", verify)

    secret = "-----BEGIN PRIVATE KEY-----MIIEvQ"
    out = run(rbc.save_coinbase(
        rbc.CoinbaseCredentials(key_name="organizations/abc/apiKeys/xyz9", private_key=secret),
        user=USER))

    assert verified["key_name"] == "organizations/abc/apiKeys/xyz9"
    stored = db.broker_connections.rows[0]
    assert stored["user_id"] == "user_1" and stored["broker"] == "coinbase"
    assert stored["verified"] is True
    assert stored["key_name_enc"] == "enc:organizations/abc/apiKeys/xyz9"
    assert stored["private_key_enc"] == "enc:" + secret
    assert "private_key" not in stored and "key_name" not in stored
    assert stored["key_hint"] == "…xyz9"
    assert set(out) == {"broker", "saved", "verified", "key_hint", "updated_at"}
    assert secret not in repr(out)


def test_save_rejects_short_credentials():
    with pytest.raises(Exception):
        rbc.CoinbaseCredentials(key_name="short", private_key="tiny")


def test_delete_reports_missing_connection(monkeypatch):
    monkeypatch.setattr(rbc, "db", FakeDb())
    with pytest.raises(HTTPException) as err:
        run(rbc.delete_coinbase(user=USER))
    assert err.value.status_code == 404


def test_delete_removes_only_that_users_connection(monkeypatch):
    db = FakeDb(FakeConnections([
        {"user_id": "user_1", "broker": "coinbase", "verified": True},
        {"user_id": "user_2", "broker": "coinbase", "verified": True},
    ]))
    monkeypatch.setattr(rbc, "db", db)
    out = run(rbc.delete_coinbase(user=USER))
    assert out == {"broker": "coinbase", "saved": False}
    assert [r["user_id"] for r in db.broker_connections.rows] == ["user_2"]


def test_disabled_account_cannot_save(monkeypatch):
    monkeypatch.setattr(rbc, "db", FakeDb())
    monkeypatch.setattr(rbc, "vault", lambda: FakeFernet())
    with pytest.raises(HTTPException) as err:
        run(rbc.save_coinbase(
            rbc.CoinbaseCredentials(key_name="organizations/abc/apiKeys/name", private_key="k" * 40),
            user={**USER, "account_status": "disabled"}))
    assert err.value.status_code == 403
