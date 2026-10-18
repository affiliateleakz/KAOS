import asyncio
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

import routes_coinbase as rc


def run(c):
    return asyncio.run(c)


class Req:
    headers = {"authorization": "Bearer x"}


class Client:
    def __init__(self):
        self.placed = []
        self.cancelled = []

    def preview_market_order_buy(self, product_id, quote_size):
        return {"order_total": "10.06", "commission_total": "0.06", "best_ask": "80000", "secret": "no"}

    def market_order_buy(self, **k):
        self.placed.append(k)

    def cancel_orders(self, order_ids):
        self.cancelled.append(order_ids)
        return {"results": [{"success": True, "order_id": order_ids[0]}]}


@pytest.fixture
def env(monkeypatch):
    client = Client()
    monkeypatch.setattr(rc, "connection", AsyncMock(return_value={}))
    monkeypatch.setattr(rc, "make_client", lambda conn: client)
    monkeypatch.delenv("KAOS_COINBASE_LIVE_ORDERS", raising=False)
    monkeypatch.setattr(rc, "get_entitlements", AsyncMock(return_value={"botAccess": True}))
    monkeypatch.setattr(rc, "get_setting", AsyncMock(return_value=False))
    return client


def test_preview_never_places_and_works_while_disabled(env):
    out = run(rc.preview(rc.PreviewRequest(product_id="BTC-USD", side="BUY", quote_size="10"), user={"id": "u"}))
    assert out["placed"] is False and out["live_orders_enabled"] is False
    assert out["preview"]["commission_total"] == "0.06" and "secret" not in out["preview"]
    assert env.placed == []


def test_preview_rejects_bad_sizes(env):
    with pytest.raises(HTTPException):
        run(rc.preview(rc.PreviewRequest(product_id="BTC-USD", side="BUY", base_size="1"), user={"id": "u"}))


def test_cancel_and_submit_blocked_while_live_disabled(env):
    user = {"id": "u", "membership_status": "ACTIVE"}
    with pytest.raises(HTTPException) as e:
        run(rc.cancel(rc.ReconcileRequest(client_order_id="c" * 16), Req(), user))
    assert e.value.status_code == 403
    with pytest.raises(HTTPException) as e:
        run(rc.order(rc.OrderRequest(client_order_id="c" * 16, product_id="BTC-USD", side="BUY", quote_size="5"), Req(), user))
    assert e.value.status_code == 403 and env.placed == [] and env.cancelled == []


def test_platform_emergency_stop_blocks_even_when_enabled(env, monkeypatch):
    monkeypatch.setenv("KAOS_COINBASE_LIVE_ORDERS", "enabled")
    monkeypatch.setattr(rc, "get_entitlements", AsyncMock(return_value={"botAccess": True}))
    monkeypatch.setattr(rc, "get_setting", AsyncMock(return_value=True))
    fake = type("DB", (), {})()
    fake.coinbase_live_consent = type("C", (), {"find_one": AsyncMock(return_value={"enabled": True, "expires_at": "2999-01-01T00:00:00+00:00"})})()
    fake.coinbase_emergency_stops = type("C", (), {"find_one": AsyncMock(return_value=None)})()
    monkeypatch.setattr(rc, "db", fake)
    with pytest.raises(HTTPException) as e:
        run(rc.authorized(Req(), {"id": "u", "membership_status": "ACTIVE"}))
    assert e.value.detail == "Platform emergency stop active"
