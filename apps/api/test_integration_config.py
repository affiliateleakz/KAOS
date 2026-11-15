import os
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "kaos_test")
os.environ.setdefault("JWT_SECRET", "test-only-jwt-secret")
os.environ.pop("KAOS_INTEGRATION_VAULT_KEY", None)
os.environ.pop("KAOS_BROKER_VAULT_KEY", None)

import asyncio

import pytest
from fastapi import HTTPException

import integration_config as ic


def run(coro):
    return asyncio.run(coro)


class FakeSecrets:
    def __init__(self):
        self.rows = {}

    def find(self, query, projection=None):
        rows = list(self.rows.values())

        class Cursor:
            async def to_list(self, limit):
                return rows[:limit]
        return Cursor()

    async def find_one(self, query, projection=None):
        return self.rows.get(query.get("provider"))

    async def update_one(self, query, update, upsert=False):
        provider = query["provider"]
        row = self.rows.setdefault(provider, {"provider": provider})
        row.update(update.get("$set", {}))

    async def delete_one(self, query):
        self.rows.pop(query["provider"], None)


class FakeDb:
    def __init__(self):
        self.kaos_integration_secrets = FakeSecrets()


@pytest.fixture(autouse=True)
def fake_db(monkeypatch):
    ic._ENV_ORIGINAL.clear()
    ic._APPLIED.clear()
    db = FakeDb()
    monkeypatch.setattr(ic, "db", db)
    for entry in ic.INTEGRATIONS:
        for field in entry["fields"]:
            monkeypatch.delenv(field["env"], raising=False)
    return db


ADMIN = {"id": "u_admin", "email": "owner@example.com", "role": "admin"}


def test_catalog_describes_every_integration_for_a_human(fake_db):
    body = run(ic.catalog())
    assert body["vault_ready"] is True
    ids = {i["id"] for i in body["integrations"]}
    assert {"alpaca", "sec_edgar", "congress", "google", "stripe"} <= ids
    for item in body["integrations"]:
        assert item["purpose"] and item["get_it_at"].startswith("http")
        assert item["cost"], item["id"]
        assert item["powers"], item["id"]
        assert isinstance(item["fields"], list) and item["fields"]


def test_catalog_never_exposes_a_stored_secret(fake_db):
    run(ic.save("alpaca", {"APCA_API_KEY_ID": "PKTESTKEY123456", "APCA_API_SECRET_KEY": "s" * 40}, ADMIN))
    blob = repr(run(ic.catalog()))
    assert "PKTESTKEY123456" not in blob
    assert "s" * 40 not in blob
    alpaca = next(i for i in run(ic.catalog())["integrations"] if i["id"] == "alpaca")
    key_field = next(f for f in alpaca["fields"] if f["env"] == "APCA_API_KEY_ID")
    assert key_field["set"] is True and key_field["source"] == "admin"
    assert key_field["preview"] == "…3456"


def test_saved_key_becomes_active_immediately(fake_db):
    assert not os.getenv("APCA_API_KEY_ID")
    run(ic.save("alpaca", {"APCA_API_KEY_ID": "PKGOODKEY12345", "APCA_API_SECRET_KEY": "z" * 44}, ADMIN))
    # Any existing provider code reading the environment now sees the key.
    assert os.getenv("APCA_API_KEY_ID") == "PKGOODKEY12345"
    assert os.getenv("APCA_API_SECRET_KEY") == "z" * 44


def test_stored_values_are_encrypted_at_rest(fake_db):
    run(ic.save("openai", {"OPENAI_API_KEY": "sk-super-secret-value"}, ADMIN))
    stored = fake_db.kaos_integration_secrets.rows["openai"]
    assert "sk-super-secret-value" not in repr(stored)
    assert stored["values_enc"]["OPENAI_API_KEY"].startswith("gAAAAA")


def test_removing_a_key_restores_the_environment_value(fake_db, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-from-env-file")
    run(ic.save("openai", {"OPENAI_API_KEY": "sk-from-admin-panel"}, ADMIN))
    assert os.getenv("OPENAI_API_KEY") == "sk-from-admin-panel"
    run(ic.remove("openai", ADMIN))
    assert os.getenv("OPENAI_API_KEY") == "sk-from-env-file"


def test_removing_a_key_that_only_existed_in_the_panel_unsets_it(fake_db):
    run(ic.save("openai", {"OPENAI_API_KEY": "sk-only-in-panel"}, ADMIN))
    run(ic.remove("openai", ADMIN))
    assert os.getenv("OPENAI_API_KEY") is None


def test_toggle_field_maps_on_off_to_the_env_value(fake_db):
    run(ic.save("congress", {"KAOS_HOUSE_DISCLOSURE_RIGHTS": "on"}, ADMIN))
    assert os.getenv("KAOS_HOUSE_DISCLOSURE_RIGHTS") == "approved"
    run(ic.save("congress", {"KAOS_HOUSE_DISCLOSURE_RIGHTS": "off"}, ADMIN))
    assert os.getenv("KAOS_HOUSE_DISCLOSURE_RIGHTS") == ""


def test_rejects_fields_the_integration_does_not_have(fake_db):
    with pytest.raises(HTTPException) as err:
        run(ic.save("alpaca", {"STRIPE_SECRET_KEY": "sk_live_whatever"}, ADMIN))
    assert err.value.status_code == 422


def test_rejects_unknown_integration(fake_db):
    with pytest.raises(HTTPException) as err:
        run(ic.save("not-a-provider", {"X": "y"}, ADMIN))
    assert err.value.status_code == 404


def test_rejects_short_secret(fake_db):
    with pytest.raises(HTTPException) as err:
        run(ic.save("openai", {"OPENAI_API_KEY": "short"}, ADMIN))
    assert err.value.status_code == 422


def test_remove_reports_nothing_stored(fake_db):
    with pytest.raises(HTTPException) as err:
        run(ic.remove("openai", ADMIN))
    assert err.value.status_code == 404


def test_probe_without_credentials_says_what_is_missing(fake_db):
    result = run(ic.probe("alpaca"))
    assert result["ok"] is False
    assert "Add the API Key ID" in result["detail"]


def test_probe_rejects_a_malformed_google_client_id(fake_db, monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "not-a-google-client")
    result = run(ic.probe("google"))
    assert result["ok"] is False
    assert "apps.googleusercontent.com" in result["detail"]


def test_probe_accepts_a_well_formed_google_client_id(fake_db, monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "123-abc.apps.googleusercontent.com")
    assert run(ic.probe("google"))["ok"] is True


def test_vault_falls_back_to_jwt_secret_only_when_long_enough(fake_db, monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "short")
    with pytest.raises(HTTPException) as err:
        run(ic.save("openai", {"OPENAI_API_KEY": "sk-abcdefghij"}, ADMIN))
    assert err.value.status_code == 503
