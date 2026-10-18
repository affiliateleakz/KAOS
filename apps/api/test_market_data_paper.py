"""Market-data-driven paper fills: server-fetched timestamped quotes, bid/ask fills, staleness, provenance."""
import os
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "kaos_test")
import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import market_data
import routes_paper
from market_data import Quote, parse_coinbase_ticker, QuoteUnavailable


def run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


class _Cursor:
    def __init__(self, docs):
        self.docs = docs

    def sort(self, key, direction):
        self.docs.sort(key=lambda d: d.get(key) or "", reverse=direction < 0)
        return self

    async def to_list(self, n):
        return self.docs[:n]


class FakeCollection:
    def __init__(self):
        self.docs = []

    def _match(self, d, q):
        return all(d.get(k) == v for k, v in q.items())

    async def find_one(self, q, proj=None):
        return next((dict(d) for d in self.docs if self._match(d, q)), None)

    def find(self, q, proj=None):
        return _Cursor([dict(d) for d in self.docs if self._match(d, q)])

    async def insert_one(self, doc):
        self.docs.append(dict(doc))

    async def update_one(self, q, upd, upsert=False):
        hit = next((d for d in self.docs if self._match(d, q)), None)
        if hit is not None:
            hit.update(upd.get("$set", {}))
        elif upsert:
            self.docs.append({**q, **upd.get("$setOnInsert", {}), **upd.get("$set", {})})
        return SimpleNamespace(modified_count=1 if hit is not None else 0)


class FakeDB:
    def __init__(self):
        self.paper_orders, self.paper_order_rejections = FakeCollection(), FakeCollection()
        self.paper_signals, self.paper_sessions = FakeCollection(), FakeCollection()


@pytest.fixture
def env(monkeypatch):
    fdb, state = FakeDB(), {"quote_age": 1, "kill": False, "calls": 0}

    async def fetch(symbol):
        state["calls"] += 1
        if state.get("down"):
            raise QuoteUnavailable("provider unreachable")
        now = datetime.now(timezone.utc)
        return Quote(symbol, Decimal(state.get("bid", "100")), Decimal(state.get("ask", "101")), Decimal("100.5"),
                     now - timedelta(seconds=state["quote_age"]), now, market_data.COINBASE_PUBLIC_SOURCE)

    async def setting(key, default=None):
        return state["kill"] if key == "paper_kill_switch" else default

    monkeypatch.setattr(routes_paper, "db", fdb)
    monkeypatch.setattr(routes_paper, "get_setting", setting)
    async def candles(symbol, granularity):
        if state.get("rows") is not None:
            return state["rows"]
        t = int(datetime.now(timezone.utc).timestamp()) // 60 * 60  # newest bar still forming
        return [[t - 60 * i, 99.0, 101.0, 100.0, 100.5, 1.0] for i in range(120)]

    monkeypatch.setattr(market_data, "fetch_crypto_quote", fetch)
    monkeypatch.setattr(market_data, "fetch_crypto_candles", candles)
    return fdb, state, {"id": f"u-{uuid.uuid4().hex[:8]}"}


def order(user, side="BUY", qty="10", price=None, cid=None, symbol="BTC-USD", asset="CRYPTO_SPOT"):
    return run(routes_paper._submit(user, symbol, asset, side, qty, price, cid or uuid.uuid4().hex))


def test_parse_coinbase_ticker_keeps_timestamp_and_bid_ask():
    q = parse_coinbase_ticker("BTC-USD", {"bid": "80993.82", "ask": "80993.83", "price": "80993.82",
                                          "time": "2026-10-18T18:44:45.573353253Z"}, datetime.now(timezone.utc))
    assert (q.bid, q.ask) == (Decimal("80993.82"), Decimal("80993.83"))
    assert q.quote_time == datetime(2026, 10, 18, 18, 44, 45, 573353, tzinfo=timezone.utc)
    with pytest.raises(QuoteUnavailable):
        parse_coinbase_ticker("BTC-USD", {"bid": "2", "ask": "1", "price": "1", "time": "2026-10-18T18:44:45Z"},
                              datetime.now(timezone.utc))


def test_no_authorized_feed_for_other_asset_classes(env):
    with pytest.raises(HTTPException) as e:
        order(env[2], asset="EQUITY", symbol="SPY")
    assert e.value.status_code == 503 and "No authorized market-data feed for EQUITY" in e.value.detail


def test_market_data_buy_fills_at_ask_with_provenance_then_sell_at_bid(env):
    fdb, state, user = env
    buy = order(user)
    assert buy["execution_kind"] == "market_data_paper" and buy["fill_price"] == "101"
    assert buy["quote"]["source"] == "coinbase_exchange_public_ticker" and buy["quote"]["quote_time"]
    assert buy["paper"] is True and buy["broker"] == "kaos_paper"
    sell = run(routes_paper._submit(user, "BTC-USD", "CRYPTO_SPOT", "SELL", "0", None, "close-" + uuid.uuid4().hex,
                                    close_all=True))
    assert sell["fill_price"] == "100" and sell["execution_kind"] == "market_data_paper"
    assert Decimal(sell["realized_pnl"]) < 0  # crossing the spread costs money


def test_stale_quote_rejected_by_risk_engine(env):
    fdb, state, user = env
    state["quote_age"] = 60
    with pytest.raises(HTTPException) as e:
        order(user)
    assert e.value.status_code == 422 and "stale" in e.value.detail
    assert fdb.paper_order_rejections.docs[0]["reason"] == "Missing or stale market quote"


def test_kill_switch_blocks_market_data_orders(env):
    fdb, state, user = env
    state["kill"] = True
    with pytest.raises(HTTPException):
        order(user)
    assert fdb.paper_orders.docs == []


def test_retry_is_idempotent_without_refetching_and_conflicts_refused(env):
    fdb, state, user = env
    first = order(user, cid="retry-" + user["id"])
    calls = state["calls"]
    assert order(user, cid="retry-" + user["id"]) == first and state["calls"] == calls
    with pytest.raises(HTTPException) as e:
        order(user, qty="20", cid="retry-" + user["id"])
    assert e.value.status_code == 409


def test_manual_price_is_labelled_demo(env):
    o = order(env[2], price="50")
    assert o["execution_kind"] == "manual_demo" and o["quote"] is None and o["fill_price"] == "50"


def test_book_survives_reconnect_from_stored_orders(env):
    fdb, state, user = env
    order(user)
    view = routes_paper.book_view(run(routes_paper._user_book(user, datetime.now(timezone.utc))))
    assert view["cash"] == "89.94" and view["fees_paid"] == "0.06"  # $10 + 0.6% simulated fee
    assert view["positions"][0]["symbol"] == "BTC-USD"


def test_fee_charged_on_both_sides_and_in_realized_pnl(env):
    fdb, state, user = env
    buy = order(user)
    assert buy["fee"] == "0.06000000" and buy["fee_rate"] == "0.006"
    sell = run(routes_paper._submit(user, "BTC-USD", "CRYPTO_SPOT", "SELL", "0", None, uuid.uuid4().hex, close_all=True))
    # proceeds 10/101*100 = 9.90099..., minus sell fee, minus cost 10.06
    assert Decimal(sell["realized_pnl"]) == Decimal("-0.22")


def test_candles_drop_forming_bar_and_flat_market_holds_with_reason(env):
    c = run(market_data.get_candles("BTC-USD", "CRYPTO_SPOT", 60))
    assert c["source"] == market_data.COINBASE_PUBLIC_SOURCE and len(c["candles"]) == 119
    assert c["candles"][0]["time"] < c["candles"][-1]["time"]
    sig = run(routes_paper.generate_signal("BTC-USD", routes_paper.ExecuteSignalReq(notional="10"), 60, env[2]))
    assert sig["action"] == "HOLD" and sig["reasons"] and sig["risk"]["approved"] is False
    assert sig["strategy"] == "KAOS Structure v2" and "FAIL" in sig["strategy_status"]
    with pytest.raises(HTTPException) as e:
        run(routes_paper.execute_signal(sig["signal_id"], env[2]))
    assert e.value.status_code == 409


def test_buy_signal_risk_approved_executes_once_at_market_price(env, monkeypatch):
    fdb, state, user = env
    monkeypatch.setattr(routes_paper.kaos_structure_v2, "evaluate", lambda c: {
        "action": "BUY", "setup": "breakout_long", "reasons": ["test breakout"], "indicators": {}, "candle_time": 0})
    sig = run(routes_paper.generate_signal("BTC-USD", routes_paper.ExecuteSignalReq(notional="10"), 60, user))
    assert sig["risk"]["approved"] is True and sig["status"] == "PENDING"
    o = run(routes_paper.execute_signal(sig["signal_id"], user))
    assert o["signal_id"] == sig["signal_id"] and o["fill_price"] == "101" and o["execution_kind"] == "market_data_paper"
    assert run(routes_paper.execute_signal(sig["signal_id"], user)) == o  # refresh/retry: no second order
    assert len(fdb.paper_orders.docs) == 1
    assert fdb.paper_signals.docs[0]["status"] == "EXECUTED"


def test_risk_rejects_oversized_signal_and_sell_without_position(env, monkeypatch):
    fdb, state, user = env
    act = {"a": "BUY"}
    monkeypatch.setattr(routes_paper.kaos_structure_v2, "evaluate", lambda c: {
        "action": act["a"], "setup": "x", "reasons": ["r"], "indicators": {}, "candle_time": 0})
    big = run(routes_paper.generate_signal("BTC-USD", routes_paper.ExecuteSignalReq(notional="500"), 60, user))
    assert big["risk"]["approved"] is False and big["status"] == "NOT_TRADED"
    act["a"] = "SELL"
    s = run(routes_paper.generate_signal("BTC-USD", routes_paper.ExecuteSignalReq(notional="10"), 60, user))
    assert s["risk"]["approved"] is False and "long-only" in s["risk"]["reason"]


def test_session_persists_and_unavailable_broker_refused(env):
    user = env[2]
    run(routes_paper.put_session(routes_paper.SessionReq(symbol="eth-usd", notional="5"), user))
    assert run(routes_paper.get_session(user))["symbol"] == "ETH-USD"
    with pytest.raises(HTTPException) as e:
        run(routes_paper.put_session(routes_paper.SessionReq(broker="pocket_option"), user))
    assert "market-data" in e.value.detail


import json
import pathlib

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def _recorded_rows(name):
    """Recorded Coinbase public candles -> Coinbase API row order ([t, low, high, open, close, vol], newest first)."""
    rec = json.loads((FIXTURES / name).read_text())
    return rec, [[c["time"], c["low"], c["high"], c["open"], c["close"], c["volume"]] for c in reversed(rec["candles"])]


@pytest.mark.parametrize("name,setup", [("coinbase_btc_usd_5m_breakout_long.json", "breakout_long"),
                                        ("coinbase_eth_usd_15m_pullback_long.json", "pullback_long")])
def test_recorded_market_candles_produce_real_strategy_signal(name, setup):
    rec, _ = _recorded_rows(name)
    r = routes_paper.kaos_structure_v2.evaluate(rec["candles"])
    assert r["action"] == "BUY" and r["setup"] == setup and r["reasons"][0].lower().startswith(setup.split("_")[0])


def _recorded_signal(env, user=None, notional="10"):
    fdb, state, u = env
    rec, rows = _recorded_rows("coinbase_btc_usd_5m_breakout_long.json")
    state["rows"] = rows
    return run(routes_paper.generate_signal("BTC-USD", routes_paper.ExecuteSignalReq(notional=notional), 300, user or u))


def test_recorded_signal_to_fill_and_execution_risk_recorded(env):
    fdb, state, user = env
    sig = _recorded_signal(env)
    assert sig["action"] == "BUY" and sig["setup"] == "breakout_long" and sig["risk"]["approved"]
    o = run(routes_paper.execute_signal(sig["signal_id"], user))
    assert o["fill_price"] == "101" and o["quote"]["source"] == market_data.COINBASE_PUBLIC_SOURCE
    stored = fdb.paper_signals.docs[0]
    assert stored["status"] == "EXECUTED" and stored["risk_at_execution"]["approved"] is True


def test_concurrent_executes_fill_once(env):
    fdb, state, user = env
    sig = _recorded_signal(env)

    async def both():
        return await asyncio.gather(routes_paper.execute_signal(sig["signal_id"], user),
                                    routes_paper.execute_signal(sig["signal_id"], user), return_exceptions=True)
    res = asyncio.new_event_loop().run_until_complete(both())
    assert len(fdb.paper_orders.docs) == 1
    assert any(isinstance(r, dict) for r in res)


def test_kill_switch_after_signal_rejects_at_execution(env):
    fdb, state, user = env
    sig = _recorded_signal(env)
    state["kill"] = True
    with pytest.raises(HTTPException) as e:
        run(routes_paper.execute_signal(sig["signal_id"], user))
    assert e.value.status_code == 422 and not fdb.paper_orders.docs
    s = fdb.paper_signals.docs[0]
    assert s["status"] == "REJECTED" and s["risk_at_execution"]["approved"] is False


@pytest.mark.parametrize("fault", ["down", "stale", "wide"])
def test_execution_never_fills_on_bad_quote(env, fault):
    fdb, state, user = env
    sig = _recorded_signal(env)
    if fault == "down":
        state["down"] = True
    elif fault == "stale":
        state["quote_age"] = 30
    else:
        state["bid"], state["ask"] = "100", "103"
    with pytest.raises(HTTPException) as e:
        run(routes_paper.execute_signal(sig["signal_id"], user))
    assert e.value.status_code in (422, 503) and not fdb.paper_orders.docs
    assert fdb.paper_signals.docs[0]["status"] == "REJECTED"
    with pytest.raises(HTTPException):  # a rejected signal cannot be retried into a fill at an old price
        run(routes_paper.execute_signal(sig["signal_id"], user))
    assert not fdb.paper_orders.docs


def test_other_user_cannot_see_or_execute_signal(env):
    fdb, state, user = env
    sig = _recorded_signal(env)
    eve = {"id": "user_eve", "email": "eve@example.com"}
    with pytest.raises(HTTPException) as e:
        run(routes_paper.execute_signal(sig["signal_id"], eve))
    assert e.value.status_code == 404
    assert run(routes_paper.list_signals(eve))["signals"] == []
    assert not fdb.paper_orders.docs


def test_session_fee_and_slippage_applied_and_bounded(env):
    fdb, state, user = env
    run(routes_paper.put_session(routes_paper.SessionReq(fee_rate="0.001", slippage_bps=10), user))
    o = order(user)
    assert o["fill_price"] == "101.101" and o["fee_rate"] == "0.001" and o["slippage_bps"] == 10
    assert o["fee"] == "0.01000000" and "not a Coinbase" in o["fee_model"]
    for bad in [routes_paper.SessionReq(fee_rate="0.05"), routes_paper.SessionReq(fee_rate="-0.001"),
                routes_paper.SessionReq(slippage_bps=500)]:
        with pytest.raises(HTTPException) as e:
            run(routes_paper.put_session(bad, user))
        assert e.value.status_code == 422
