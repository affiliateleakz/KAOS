import asyncio
import json

import httpx
import pytest
from cryptography.fernet import Fernet
from fastapi import HTTPException
from unittest.mock import AsyncMock

import routes_broker_alpaca as ra


def run(c):
    return asyncio.run(c)


class Coll:
    def __init__(self): self.rows = {}
    async def update_one(self, q, u, upsert=False): self.rows[(q["user_id"], q["broker"])] = {**u["$set"]}
    async def find_one(self, q, proj=None):
        r = self.rows.get((q["user_id"], q["broker"]))
        return dict(r) if r and r.get("verified") == q.get("verified", r.get("verified")) else None
    async def delete_many(self, q): self.rows.pop((q["user_id"], q["broker"]), None)


KEY, SECRET = "PKTESTKEY12345678", "s" * 40
CALLS = []


def handler(req: httpx.Request):
    CALLS.append((req.method, req.url.host, req.url.path))
    if req.headers.get("APCA-API-SECRET-KEY") != SECRET:
        return httpx.Response(401, json={"message": "unauthorized"})
    data = {"/v2/account": {"status": "ACTIVE", "currency": "USD", "cash": "1000", "buying_power": "2000", "equity": "1500"},
            "/v2/positions": [{"symbol": "AAPL", "qty": "2", "avg_entry_price": "200", "current_price": "210",
                               "market_value": "420", "unrealized_pl": "20"}],
            "/v2/orders": [{"id": "o1", "symbol": "SPY", "side": "buy", "type": "limit", "qty": "1", "status": "new"}],
            "/v2/account/activities/FILL": [{"id": "f1", "symbol": "AAPL", "side": "buy", "qty": "2", "price": "200"}]}
    return httpx.Response(200, json=data[req.url.path])


@pytest.fixture
def env(monkeypatch):
    CALLS.clear()
    monkeypatch.setenv("KAOS_BROKER_VAULT_KEY", Fernet.generate_key().decode())
    monkeypatch.delenv("KAOS_BROKER_VAULT_PREVIOUS_KEYS", raising=False)
    db = type("DB", (), {})(); db.broker_connections = Coll()
    monkeypatch.setattr(ra, "db", db)
    monkeypatch.setattr(ra, "audit_log", AsyncMock())
    monkeypatch.setattr(ra, "transport", httpx.MockTransport(handler))
    return db


USER = {"id": "u1"}


def test_connect_encrypts_and_hides_secret(env):
    out = run(ra.connect(ra.AlpacaConnect(key_id=KEY, secret_key=SECRET), USER))
    assert out["connected"] and out["environment"] == "paper" and out["key_hint"] == "…5678"
    row = env.broker_connections.rows[("u1", "alpaca")]
    assert SECRET not in json.dumps(row) and KEY not in json.dumps(row) and SECRET not in json.dumps(out)
    assert CALLS[0][1] == "paper-api.alpaca.markets"


def test_bad_key_rejected_without_echo(env):
    with pytest.raises(HTTPException) as e:
        run(ra.connect(ra.AlpacaConnect(key_id=KEY, secret_key="w" * 40), USER))
    assert e.value.status_code == 422 and "w" * 40 not in e.value.detail
    assert not env.broker_connections.rows


def test_account_view_is_read_only(env):
    run(ra.connect(ra.AlpacaConnect(key_id=KEY, secret_key=SECRET), USER))
    out = run(ra.account(USER))
    assert out["account"]["buying_power"] == "2000" and out["positions"][0]["unrealized_pl"] == "20"
    assert out["open_orders"][0]["symbol"] == "SPY" and out["fills"][0]["id"] == "f1"
    assert all(m == "GET" for m, _, _ in CALLS)


def test_isolation_and_disconnect(env):
    run(ra.connect(ra.AlpacaConnect(key_id=KEY, secret_key=SECRET), USER))
    with pytest.raises(HTTPException) as e:
        run(ra.account({"id": "other"}))
    assert e.value.status_code == 404
    run(ra.disconnect(USER))
    assert run(ra.status(USER)) == {"connected": False, "broker": "alpaca"}


def test_live_environment_uses_live_host(env):
    run(ra.connect(ra.AlpacaConnect(key_id=KEY, secret_key=SECRET, environment="live"), USER))
    assert CALLS[-1][1] == "api.alpaca.markets"
