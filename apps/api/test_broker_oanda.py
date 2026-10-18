"""Fail-closed, read-only OANDA practice connector tests."""
import asyncio
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
import routes_broker_oanda as oanda

def run(coro):
    return asyncio.run(coro)

def test_request_allowlist():
    for path in ("/v3/accounts/123/orders", "/v3/accounts/123/transactions", "https://bad.example"):
        with pytest.raises(HTTPException) as e:
            run(oanda.oanda_get(path, "secret"))
        assert e.value.status_code == 400

def test_readonly_account_projection(monkeypatch):
    monkeypatch.setattr(oanda, "_credentials", AsyncMock(return_value=("123-456", "private-token")))
    async def fake_get(path, token):
        assert token == "private-token"
        if path.endswith("/summary"):
            return {"account": {"id": "123-456", "currency": "USD", "balance": "10000", "secret": "NEVER"}}
        if path.endswith("/openPositions"):
            return {"positions": [{"instrument": "EUR_USD", "unrealizedPL": "5", "secret": "NEVER"}]}
        if path.endswith("/pendingOrders"):
            return {"orders": [{"id": "a1", "instrument": "EUR_USD", "state": "PENDING", "secret": "NEVER"}]}
        raise AssertionError(path)
    monkeypatch.setattr(oanda, "oanda_get", fake_get)
    result = run(oanda.account(user={"id": "member"}))
    assert result["environment"] == "practice"
    assert result["account"]["balance"] == "10000"
    assert result["positions"][0]["instrument"] == "EUR_USD"
    assert result["orders"][0]["state"] == "PENDING"
    assert "NEVER" not in str(result) and "private-token" not in str(result)

def test_bad_upstream_fails_closed(monkeypatch):
    monkeypatch.setattr(oanda, "_credentials", AsyncMock(return_value=("123", "token")))
    async def fake_get(path, token):
        return {"account": {"id": "123"}} if path.endswith("summary") else {}
    monkeypatch.setattr(oanda, "oanda_get", fake_get)
    with pytest.raises(HTTPException) as exc:
        run(oanda.account(user={"id": "member"}))
    assert exc.value.status_code == 502
