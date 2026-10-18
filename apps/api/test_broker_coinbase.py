import asyncio
import json

import pytest
from cryptography.fernet import Fernet
from fastapi import HTTPException

import routes_broker_coinbase as rb

KEY = "organizations/org-1/apiKeys/key-abcd"
PEM = "-----BEGIN EC PRIVATE KEY-----\nMHcCAQEEIFake\n-----END EC PRIVATE KEY-----"


def run(c):
    return asyncio.run(c)


class Coll:
    def __init__(self):
        self.rows = []

    async def find_one(self, q, proj=None):
        return next((dict(r) for r in self.rows if all(r.get(k) == v for k, v in q.items())), None)

    async def update_one(self, q, u, upsert=False):
        r = next((r for r in self.rows if all(r.get(k) == v for k, v in q.items())), None)
        if r is None:
            r = dict(q)
            self.rows.append(r)
        r.update(u["$set"])

    def find(self, q, proj=None):
        rows = [dict(r) for r in self.rows if all(r.get(k) == v for k, v in q.items())]
        class C:
            async def to_list(self, n):
                return rows
        return C()

    async def delete_many(self, q):
        self.rows = [r for r in self.rows if not all(r.get(k) == v for k, v in q.items())]


class FakeClient:
    perms = {"can_view": True, "can_trade": False, "can_transfer": False, "portfolio_type": "DEFAULT"}
    calls = 0

    def __init__(self, key, secret):
        assert (key, secret) == (KEY, PEM)

    def get_api_key_permissions(self):
        return dict(self.perms)

    def get_accounts(self, limit=None):
        FakeClient.calls += 1
        return {"accounts": [{"currency": "BTC", "available_balance": {"value": "0.01"}, "hold": {"value": "0"}},
                             {"currency": "ETH", "available_balance": {"value": "0"}, "hold": {"value": "0"}}]}

    def list_orders(self, order_status=None, limit=None):
        return {"orders": [{"order_id": "o1", "product_id": "BTC-USD", "side": "BUY", "status": "OPEN", "secret": "x"}]}

    def get_fills(self, limit=None):
        return {"fills": [{"trade_id": "t1", "order_id": "o0", "price": "80000", "size": "0.001", "commission": "0.48"}]}

    def get_products(self, product_type=None, limit=None):
        return {"products": [{"product_id": "BTC-USD", "price": "80000", "quote_currency_id": "USD"},
                             {"product_id": "BTC-EUR", "price": "70000", "quote_currency_id": "EUR"}]}

    def get_transaction_summary(self):
        return {"total_fees": 1.2, "fee_tier": {"pricing_tier": "Intro 1", "maker_fee_rate": "0.006", "taker_fee_rate": "0.012"}}


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("KAOS_BROKER_VAULT_KEY", Fernet.generate_key().decode())
    monkeypatch.delenv("KAOS_COINBASE_LIVE_ORDERS", raising=False)
    fdb = type("DB", (), {})()
    fdb.broker_connections = Coll()
    audits = []

    async def audit(actor, action, *a, **k):
        audits.append((action, json.dumps(a, default=str)))

    monkeypatch.setattr(rb, "db", fdb)
    monkeypatch.setattr(rb, "audit_log", audit)
    monkeypatch.setattr(rb, "client_factory", FakeClient)
    monkeypatch.setattr(FakeClient, "perms", dict(FakeClient.perms))
    rb._cache.clear()
    return fdb, audits, {"id": "u1"}


def test_connect_encrypts_and_never_returns_secrets(env):
    fdb, audits, user = env
    out = run(rb.connect(rb.ConnectReq(key_name=KEY, private_key=PEM), user))
    stored = fdb.broker_connections.rows[0]
    blob = json.dumps(out) + json.dumps(audits)
    assert PEM not in json.dumps(stored) and KEY not in json.dumps(stored)
    assert "BEGIN" not in blob and KEY not in blob and out["key_hint"] == "…abcd"
    assert out["live_orders_enabled"] is False and out["permissions"]["can_transfer"] is False
    assert run(rb.status(user))["connection"]["saved"] is True and out["account_count"] == 2
    lst = run(rb.list_connections(user))["connections"]
    assert lst[0]["saved"] and "key_name_enc" not in lst[0] and "private_key_enc" not in lst[0]
    assert [p["product_id"] for p in run(rb.products(user))["products"]] == ["BTC-USD"]


def test_credentials_json_accepted(env):
    blob = json.dumps({"name": KEY, "privateKey": PEM})
    assert run(rb.connect(rb.ConnectReq(key_name="", private_key=blob), env[2]))["connected"]


def test_transfer_capable_key_refused(env):
    fdb, _, user = env
    FakeClient.perms["can_transfer"] = True
    with pytest.raises(HTTPException) as e:
        run(rb.connect(rb.ConnectReq(key_name=KEY, private_key=PEM), user))
    assert e.value.status_code == 422 and not fdb.broker_connections.rows


def test_malformed_key_rejected_without_calling_coinbase(env):
    with pytest.raises(HTTPException):
        run(rb.connect(rb.ConnectReq(key_name="abc", private_key=PEM), env[2]))


def test_account_view_balances_orders_fills_fees_and_cache(env):
    _, _, user = env
    run(rb.connect(rb.ConnectReq(key_name=KEY, private_key=PEM), user))
    FakeClient.calls = 0
    a = run(rb.account(user))
    run(rb.account(user))
    assert FakeClient.calls == 1
    assert a["balances"] == [{"currency": "BTC", "available": "0.01", "hold": "0"}]
    assert a["open_orders"][0]["order_id"] == "o1" and "secret" not in a["open_orders"][0]
    assert a["fills"][0]["commission"] == "0.48" and a["fees"]["taker_rate"] == "0.012"


def test_isolation_and_disconnect(env):
    _, _, user = env
    run(rb.connect(rb.ConnectReq(key_name=KEY, private_key=PEM), user))
    with pytest.raises(HTTPException) as e:
        run(rb.account({"id": "someone-else"}))
    assert e.value.status_code == 404
    run(rb.disconnect(user))
    assert run(rb.status(user))["connected"] is False


def test_coinbase_error_does_not_leak_details(env):
    _, _, user = env
    run(rb.connect(rb.ConnectReq(key_name=KEY, private_key=PEM), user))

    def boom(*a, **k):
        raise RuntimeError("Authorization: Bearer eyJsecret")
    FakeClient.get_accounts = staticmethod(boom)
    try:
        with pytest.raises(HTTPException) as e:
            run(rb.account(user))
        assert "eyJ" not in e.value.detail and e.value.status_code == 502
    finally:
        del FakeClient.get_accounts


def test_positions_average_cost_and_pnl():
    from decimal import Decimal
    from routes_broker_coinbase import positions_from
    bal = [{"currency": "BTC", "available": "0.15", "hold": "0"}, {"currency": "USD", "available": "50", "hold": "0"}]
    fills = [{"product_id": "BTC-USD", "side": "BUY", "price": "100", "size": "0.1", "commission": "0.1", "trade_time": "1"},
             {"product_id": "BTC-USD", "side": "BUY", "price": "200", "size": "0.1", "commission": "0.1", "trade_time": "2"},
             {"product_id": "BTC-USD", "side": "SELL", "price": "300", "size": "0.05", "commission": "0.1", "trade_time": "3"}]
    p, = positions_from(bal, fills, {"BTC-USD": Decimal("250")})
    assert p["cost_basis_complete"] and p["avg_cost"] == "151.00000000"
    assert p["unrealized_pnl"] == "14.85" and p["realized_pnl_recent"] == "7.35" and p["market_value"] == "37.50"


def test_positions_incomplete_basis_reports_no_pnl():
    from decimal import Decimal
    from routes_broker_coinbase import positions_from
    p, = positions_from([{"currency": "ETH", "available": "2", "hold": "0"}],
                        [{"product_id": "ETH-USD", "side": "BUY", "price": "10", "size": "1", "commission": "0"}], {"ETH-USD": Decimal("12")})
    assert not p["cost_basis_complete"] and p["unrealized_pnl"] is None and p["market_value"] == "24.00"
