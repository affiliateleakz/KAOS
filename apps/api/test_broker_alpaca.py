"""Alpaca paper account connector: no submit endpoints or real-money order path."""
import asyncio
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
import routes_broker_alpaca as alpaca

def run(coro):
    return asyncio.run(coro)

def test_endpoint_allowlist_rejects_trade_routes():
    with pytest.raises(HTTPException) as e:
        run(alpaca.alpaca_get("/v2/orders/submit", "key", "secret"))
    assert e.value.status_code == 400

def test_readonly_output_redacts_credentials(monkeypatch):
    monkeypatch.setattr(alpaca, "_credentials", AsyncMock(return_value=("key-secret", "private-secret")))
    async def fake_get(path, key, secret):
        assert key == "key-secret" and secret == "private-secret"
        if path == "/v2/account":
            return {"id": "a1", "status": "ACTIVE", "cash": "1000", "secret_key": "NEVER"}
        if path == "/v2/positions":
            return [{"symbol": "SPY", "qty": "2", "api_secret": "NEVER"}]
        if path == "/v2/orders":
            return [{"id": "o1", "symbol": "SPY", "status": "filled", "secret": "NEVER"}]
        raise AssertionError(path)
    monkeypatch.setattr(alpaca, "alpaca_get", fake_get)
    out = run(alpaca.account(user={"id": "member"}))
    assert out["environment"] == "paper"
    assert out["account"]["cash"] == "1000"
    assert out["positions"][0]["symbol"] == "SPY"
    assert out["orders"][0]["status"] == "filled"
    assert "secret" not in str(out).lower()
    assert "NEVER" not in str(out)

def test_unconnected_member_cannot_access_other_account(monkeypatch):
    class DB:
        broker_connections = None
    class Collection:
        async def find_one(self, query):
            assert query["user_id"] == "different_user"
            return None
    DB.broker_connections = Collection()
    monkeypatch.setattr(alpaca, "db", DB)
    with pytest.raises(HTTPException) as e:
        run(alpaca._credentials("different_user"))
    assert e.value.status_code == 404

def test_invalid_upstream_data_fails_closed(monkeypatch):
    monkeypatch.setattr(alpaca, "_credentials", AsyncMock(return_value=("k", "s")))
    async def bad_get(path, key, secret):
        return [] if path == "/v2/account" else {}
    monkeypatch.setattr(alpaca, "alpaca_get", bad_get)
    with pytest.raises(HTTPException) as e:
        run(alpaca.account(user={"id": "member"}))
    assert e.value.status_code == 502
