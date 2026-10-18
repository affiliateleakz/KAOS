"""Market-data-driven paper fills: server-fetched timestamped quotes, bid/ask fills, staleness, provenance."""
import os
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "kaos_test")
import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

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
        if not any(self._match(d, q) for d in self.docs) and upsert:
            self.docs.append({**q, **upd.get("$setOnInsert", {})})


class FakeDB:
    def __init__(self):
        self.paper_orders, self.paper_order_rejections = FakeCollection(), FakeCollection()


@pytest.fixture
def env(monkeypatch):
    fdb, state = FakeDB(), {"quote_age": 1, "kill": False, "calls": 0}

    async def fetch(symbol):
        state["calls"] += 1
        now = datetime.now(timezone.utc)
        return Quote(symbol, Decimal("100"), Decimal("101"), Decimal("100.5"),
                     now - timedelta(seconds=state["quote_age"]), now, market_data.COINBASE_PUBLIC_SOURCE)

    async def setting(key, default=None):
        return state["kill"] if key == "paper_kill_switch" else default

    monkeypatch.setattr(routes_paper, "db", fdb)
    monkeypatch.setattr(routes_paper, "get_setting", setting)
    monkeypatch.setattr(market_data, "fetch_crypto_quote", fetch)
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
    assert view["cash"] == "90.00" and view["positions"][0]["symbol"] == "BTC-USD"
