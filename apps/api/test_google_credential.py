import os
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "kaos_test")
os.environ.setdefault("JWT_SECRET", "test-only-jwt-secret")

import asyncio

import pytest
from fastapi import HTTPException
from starlette.responses import Response

import routes_auth


def run(coro):
    return asyncio.run(coro)


class FakeUsers:
    def __init__(self, rows=None):
        self.rows = list(rows or [])
        self.inserted = None

    async def find_one(self, query):
        for row in self.rows:
            if all(row.get(k) == v for k, v in query.items()):
                return row
        return None

    async def insert_one(self, doc):
        self.inserted = doc
        self.rows.append(doc)

    async def update_one(self, query, update):
        for row in self.rows:
            if all(row.get(k) == v for k, v in query.items()):
                row.update(update.get("$set", {}))


class FakeDb:
    def __init__(self, users=None):
        self.users = users or FakeUsers()


def credential():
    return routes_auth.GoogleCredentialReq(credential="x" * 40)


ACTIVE_USER = {
    "id": "user_1", "email": "trader@example.com", "name": "Trader", "role": "user",
    "password_hash": "$2b$12$deadbeef", "token_version": 3, "account_status": "active",
    "extension_access_revoked": False,
}


def patch_verifier(monkeypatch, result=None, error=None):
    import google.oauth2.id_token as id_token

    def fake(token, request, audience):
        assert audience == "test-client.apps.googleusercontent.com"
        if error:
            raise error
        return result

    monkeypatch.setattr(id_token, "verify_oauth2_token", fake)


def enable(monkeypatch):
    monkeypatch.setattr(routes_auth, "GOOGLE_CLIENT_ID", "test-client.apps.googleusercontent.com")


def test_refuses_when_no_client_id_configured(monkeypatch):
    monkeypatch.setattr(routes_auth, "GOOGLE_CLIENT_ID", "")
    with pytest.raises(HTTPException) as err:
        run(routes_auth.google_credential(credential(), Response()))
    assert err.value.status_code == 503


def test_rejects_a_token_google_will_not_verify(monkeypatch):
    enable(monkeypatch)
    patch_verifier(monkeypatch, error=ValueError("Wrong recipient"))
    with pytest.raises(HTTPException) as err:
        run(routes_auth.google_credential(credential(), Response()))
    assert err.value.status_code == 401


def test_rejects_unverified_google_email(monkeypatch):
    enable(monkeypatch)
    patch_verifier(monkeypatch, result={"email": "a@b.com", "email_verified": False, "sub": "1"})
    monkeypatch.setattr(routes_auth, "db", FakeDb())
    with pytest.raises(HTTPException) as err:
        run(routes_auth.google_credential(credential(), Response()))
    assert err.value.status_code == 401


def test_rejects_disabled_account(monkeypatch):
    enable(monkeypatch)
    patch_verifier(monkeypatch, result={"email": "trader@example.com", "email_verified": True, "sub": "g1"})
    monkeypatch.setattr(routes_auth, "db", FakeDb(FakeUsers([{**ACTIVE_USER, "account_status": "disabled"}])))
    with pytest.raises(HTTPException) as err:
        run(routes_auth.google_credential(credential(), Response()))
    assert err.value.status_code == 403


def test_signs_in_existing_user_and_sets_cookies(monkeypatch):
    enable(monkeypatch)
    patch_verifier(monkeypatch, result={"email": "Trader@Example.com", "email_verified": True,
                                        "sub": "g1", "name": "Trader", "picture": "https://x/y.png"})
    db = FakeDb(FakeUsers([dict(ACTIVE_USER)]))
    monkeypatch.setattr(routes_auth, "db", db)
    response = Response()

    out = run(routes_auth.google_credential(credential(), response))

    assert out["email"] == "trader@example.com"
    assert "password_hash" not in out
    cookies = ",".join(response.headers.getlist("set-cookie"))
    assert "access_token=" in cookies and "refresh_token=" in cookies
    assert "HttpOnly" in cookies and "Secure" in cookies
    assert db.users.rows[0]["google_id"] == "g1"
    assert db.users.rows[0]["email_verified"] is True


def test_creates_verified_account_for_a_new_google_user(monkeypatch):
    enable(monkeypatch)
    patch_verifier(monkeypatch, result={"email": "new@example.com", "email_verified": True,
                                        "sub": "g2", "name": "New Trader"})
    db = FakeDb()
    monkeypatch.setattr(routes_auth, "db", db)

    out = run(routes_auth.google_credential(credential(), Response()))

    assert db.users.inserted is not None
    assert db.users.inserted["auth_provider"] == "google"
    assert db.users.inserted["email_verified"] is True
    assert db.users.inserted["password_hash"] is None
    assert out["email"] == "new@example.com"
