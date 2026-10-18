import asyncio

import pytest
from fastapi import HTTPException

import broker_adapters as ba


def test_registry_is_honest():
    rows = {b["id"]: b for b in asyncio.run(ba.list_brokers())["brokers"]}
    assert set(rows) >= {"coinbase", "alpaca", "ibkr", "oanda", "kraken", "tradier", "tastytrade", "pocketoption"}
    assert rows["coinbase"]["capabilities"]["submit"] == "disabled"
    assert all(rows[b]["status"] == "planned" for b in ("alpaca", "ibkr", "oanda", "kraken", "tradier", "tastytrade", "mt5"))
    assert rows["pocketoption"]["status"] == "adapter_development"
    assert rows["coinbase"]["status"] == "authentication_implemented"  # not read_only_verified until a real account is tested
    from broker_adapters import STATES
    assert all(r["status"] in STATES for r in rows.values())


def test_unbuilt_adapter_answers_501_with_requirements():
    with pytest.raises(HTTPException) as e:
        asyncio.run(ba.broker_account("oanda", user={"id": "u"}))
    assert e.value.status_code == 501 and "API token" in e.value.detail


def test_unknown_broker_404():
    with pytest.raises(HTTPException) as e:
        asyncio.run(ba.broker_account("nope", user={"id": "u"}))
    assert e.value.status_code == 404


def test_coinbase_adapter_delegates(monkeypatch):
    import routes_broker_coinbase, routes_coinbase

    async def acct(user): return {"key_hint": "abcd", "user": user["id"]}
    async def prev(req, user): return {"placed": False, "product": req.product_id}
    monkeypatch.setattr(routes_broker_coinbase, "account", acct)
    monkeypatch.setattr(routes_coinbase, "preview", prev)
    assert asyncio.run(ba.broker_account("coinbase", user={"id": "u"}))["user"] == "u"
    out = asyncio.run(ba.broker_preview("coinbase", ba.PreviewOrder(product_id="BTC-USD", side="BUY", quote_size="5"), user={"id": "u"}))
    assert out == {"placed": False, "product": "BTC-USD"}


def test_all_17_broker_catalog_entries_fail_closed_unless_verified():
    rows = {b["id"]: b for b in asyncio.run(ba.list_brokers())["brokers"]}
    assert len(rows) == 17
    assert set(rows) >= {"robinhood", "schwab", "fidelity", "webull", "etrade",
                         "crypto_com", "tradestation", "forex_com"}
    assert all(rows[b]["status"] == "planned" for b in (
        "robinhood", "schwab", "fidelity", "webull", "etrade", "crypto_com",
        "tradestation", "forex_com"))
    for broker, details in rows.items():
        assert details["capabilities"]["account"] is False or broker == "coinbase"
        assert details["capabilities"]["submit"] is False or details["capabilities"]["submit"] == "disabled"
        assert details["status"] != "trading_approved"
        assert details["requires"]
