"""Priority 1 safety: cancel/reconcile/exits under emergency stop, and SELL exit-lock failure recovery."""
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

import coinbase_recovery_worker as worker
import routes_coinbase as rc


def run(c):
    return asyncio.run(c)


def match(doc, q):
    for k, v in q.items():
        if isinstance(v, dict) and any(x.startswith("$") for x in v):
            if "$exists" in v and (k in doc) != v["$exists"]: return False
            if "$in" in v and doc.get(k) not in v["$in"]: return False
            if "$gte" in v and not (doc.get(k) or "") >= v["$gte"]: return False
        elif doc.get(k) != v:
            return False
    return True


class Coll:
    def __init__(self, docs=(), unique=None, fail_insert=None):
        self.docs, self.unique, self.fail_insert = [dict(d) for d in docs], unique, fail_insert
    async def find_one(self, q): return next((d for d in self.docs if match(d, q)), None)
    async def count_documents(self, q): return sum(match(d, q) for d in self.docs)
    async def insert_one(self, d):
        if self.fail_insert: raise self.fail_insert
        if self.unique and any(all(x.get(k) == d.get(k) for k in self.unique) for x in self.docs): raise DuplicateKeyError("dup")
        self.docs.append(dict(d))
    async def update_one(self, q, u):
        d = next((d for d in self.docs if match(d, q)), None)
        if d:
            d.update(u.get("$set", {}))
            for k in u.get("$unset", {}): d.pop(k, None)
        return type("R", (), {"modified_count": 1 if d else 0})()
    async def delete_one(self, q):
        self.docs = [d for d in self.docs if not match(d, q)]
    def find(self, q):
        rows = [d for d in self.docs if match(d, q)]
        class C:
            def limit(self, n): return self
            def sort(self, *a): return self
            async def to_list(self, n): return rows
            def __aiter__(self): self.i = iter(rows); return self
            async def __anext__(self):
                try: return next(self.i)
                except StopIteration: raise StopAsyncIteration
        return C()


class Req:
    headers = {"authorization": "Bearer x"}


USER = {"id": "u", "membership_status": "ACTIVE"}
BUY = {"_id": "b", "user_id": "u", "broker": "coinbase", "client_order_id": "buy-0000000000001", "product_id": "BTC-USD",
       "side": "BUY", "state": "FILLED", "filled_size": "0.001", "fill_notional": "50", "fill_fees": "0.3"}


@pytest.fixture
def fake(monkeypatch):
    db = type("DB", (), {})()
    db.coinbase_order_intents = Coll([BUY], unique=("user_id", "client_order_id"))
    db.coinbase_active_slots = Coll([{"_id": "u:coinbase:BTC-USD", "user_id": "u", "client_order_id": BUY["client_order_id"]}])
    db.coinbase_live_consent = Coll([{"user_id": "u", "enabled": True, "expires_at": "2999-01-01T00:00:00+00:00", "max_order_usd": "25"}])
    db.coinbase_emergency_stops = Coll([{"user_id": "u", "stopped": True}])
    db.coinbase_account_risk = Coll()
    db.broker_connections = Coll([{"user_id": "u", "broker": "coinbase", "verified": True}])
    for m in (rc, worker):
        monkeypatch.setattr(m, "db", db)
    monkeypatch.setattr(rc, "get_entitlements", AsyncMock(return_value={"botAccess": True}))
    monkeypatch.setattr(rc, "get_setting", AsyncMock(return_value=True))  # platform stop on too
    monkeypatch.setattr(rc, "connection", AsyncMock(return_value={}))
    monkeypatch.setenv("KAOS_COINBASE_LIVE_ORDERS", "enabled")
    return db


class Client:
    def __init__(self, sell_exc=None, orders=()):
        self.sell_exc, self.orders, self.sells, self.cancels = sell_exc, list(orders), [], []
    def market_order_sell(self, **k):
        self.sells.append(k)
        if self.sell_exc: raise self.sell_exc
        return {"success": True, "success_response": {"order_id": "ex-1"}}
    def cancel_orders(self, order_ids):
        self.cancels.append(order_ids); return {"results": [{"success": True}]}
    def get_order(self, oid): raise RuntimeError("down")
    def list_orders(self, **k): return {"orders": self.orders, "has_next": False}


def sell_req(cid="sell-000000000001"):
    return rc.OrderRequest(client_order_id=cid, product_id="BTC-USD", side="SELL", base_size="0.001",
                           source_buy_client_order_id=BUY["client_order_id"])


def test_emergency_stop_blocks_buy_but_allows_exit(fake, monkeypatch):
    client = Client()
    monkeypatch.setattr(rc, "make_client", lambda c: client)
    with pytest.raises(HTTPException) as e:
        run(rc.order(rc.OrderRequest(client_order_id="buy-0000000000002", product_id="ETH-USD", side="BUY", quote_size="5"), Req(), USER))
    assert "Emergency stop" in e.value.detail
    out = run(rc.order(sell_req(), Req(), USER))
    assert out["state"] == "ACCEPTED" and len(client.sells) == 1


def test_cancel_works_with_live_disabled_consent_expired_and_stop_on(fake, monkeypatch):
    monkeypatch.setenv("KAOS_COINBASE_LIVE_ORDERS", "disabled")
    fake.coinbase_live_consent.docs.clear()
    fake.coinbase_order_intents.docs.append({"user_id": "u", "broker": "coinbase", "client_order_id": "open-00000000001",
                                             "order_id": "ex-9", "state": "OPEN", "side": "BUY", "product_id": "BTC-USD"})
    client = Client()
    monkeypatch.setattr(rc, "make_client", lambda c: client)
    out = run(rc.cancel(rc.ReconcileRequest(client_order_id="open-00000000001"), Req(), USER))
    assert out["cancel_success"] and client.cancels == [["ex-9"]]


def test_reconcile_allowed_under_stop(fake, monkeypatch):
    monkeypatch.setenv("KAOS_COINBASE_LIVE_ORDERS", "disabled")
    with pytest.raises(HTTPException) as e:  # gets past gates to the reconcile logic
        run(rc.reconcile(rc.ReconcileRequest(client_order_id="missing-000000001"), Req(), USER))
    assert e.value.status_code == 409


def test_intent_persist_failure_releases_exit_lock(fake, monkeypatch):
    fake.coinbase_order_intents.fail_insert = RuntimeError("db down")
    monkeypatch.setattr(rc, "make_client", lambda c: Client())
    with pytest.raises(HTTPException) as e:
        run(rc.order(sell_req(), Req(), USER))
    assert e.value.status_code == 503
    src = run(fake.coinbase_order_intents.find_one({"_id": "b"}))
    assert src["state"] == "FILLED" and "exit_client_order_id" not in src


def test_second_concurrent_exit_refused(fake, monkeypatch):
    monkeypatch.setattr(rc, "make_client", lambda c: Client())
    async def both():
        return await asyncio.gather(rc.order(sell_req("sell-000000000001"), Req(), USER),
                                    rc.order(sell_req("sell-000000000002"), Req(), USER), return_exceptions=True)
    res = run(both())
    assert sum(isinstance(r, dict) for r in res) == 1
    assert sum(isinstance(r, HTTPException) and r.status_code == 409 for r in res) == 1


def test_broker_timeout_keeps_lock_and_marks_unknown(fake, monkeypatch):
    monkeypatch.setattr(rc, "make_client", lambda c: Client(sell_exc=TimeoutError()))
    with pytest.raises(HTTPException) as e:
        run(rc.order(sell_req(), Req(), USER))
    assert e.value.status_code == 502
    sell = run(fake.coinbase_order_intents.find_one({"client_order_id": "sell-000000000001"}))
    src = run(fake.coinbase_order_intents.find_one({"_id": "b"}))
    assert sell["state"] == "UNKNOWN_RECONCILIATION_REQUIRED" and src["state"] == "EXIT_SUBMITTING"
    with pytest.raises(HTTPException):  # no duplicate exit while uncertain
        run(rc.order(sell_req("sell-000000000002"), Req(), USER))


def _old(minutes):
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()


def test_worker_recovers_order_id_by_client_id(fake, monkeypatch):
    fake.coinbase_order_intents.docs.append({"_id": "s", "user_id": "u", "broker": "coinbase", "client_order_id": "sell-000000000001",
        "side": "SELL", "product_id": "BTC-USD", "state": "UNKNOWN_RECONCILIATION_REQUIRED", "created_at": _old(1),
        "source_buy_client_order_id": BUY["client_order_id"]})
    client = Client(orders=[{"client_order_id": "sell-000000000001", "order_id": "ex-7"}])
    client.get_order = lambda oid: {"order": {"order_id": oid, "status": "FILLED"}}
    monkeypatch.setattr(worker, "make_client", lambda c: client)
    monkeypatch.setattr(worker, "reconcile_order", AsyncMock(return_value={"state": "FILLED"}))
    assert run(worker.resolve_one(fake.coinbase_order_intents.docs[-1])) == "FILLED"
    assert run(fake.coinbase_order_intents.find_one({"_id": "s"}))["order_id"] == "ex-7"


def test_worker_releases_exit_when_order_never_reached_exchange(fake, monkeypatch):
    src = fake.coinbase_order_intents.docs[0]; src.update(state="EXIT_SUBMITTING", exit_client_order_id="sell-000000000001")
    intent = {"_id": "s", "user_id": "u", "broker": "coinbase", "client_order_id": "sell-000000000001", "side": "SELL",
              "product_id": "BTC-USD", "state": "UNKNOWN_RECONCILIATION_REQUIRED", "created_at": _old(1),
              "source_buy_client_order_id": BUY["client_order_id"]}
    fake.coinbase_order_intents.docs.append(intent)
    monkeypatch.setattr(worker, "make_client", lambda c: Client(orders=[]))
    assert run(worker.resolve_one(intent)) == "WAITING_FOR_EXCHANGE" and src["state"] == "EXIT_SUBMITTING"
    intent["created_at"] = _old(11)
    assert run(worker.resolve_one(intent)) == "NOT_FOUND_AT_EXCHANGE"
    assert src["state"] == "FILLED" and "exit_client_order_id" not in src


def test_worker_releases_stale_lock_after_crash_before_intent_saved(fake):
    src = fake.coinbase_order_intents.docs[0]
    src.update(state="EXIT_SUBMITTING", exit_client_order_id="sell-000000000009", exit_locked_at=_old(5))
    assert run(worker.release_stale_exit_locks()) == 1 and src["state"] == "FILLED"


def test_sell_closed_unfilled_releases_position(fake):
    src = fake.coinbase_order_intents.docs[0]; src.update(state="EXIT_SUBMITTING", exit_client_order_id="sell-000000000001")
    run(rc.release_exit_lock("u", BUY["client_order_id"], "sell-other-0000001"))
    assert src["state"] == "EXIT_SUBMITTING"  # different exit id: untouched
    run(rc.release_exit_lock("u", BUY["client_order_id"], "sell-000000000001"))
    assert src["state"] == "FILLED"
