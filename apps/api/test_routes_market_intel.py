"""Offline API tests for the Market Intelligence Centre (no network, no Mongo)."""
import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "kaos_test")
os.environ.setdefault("JWT_SECRET", "test-secret")

import routes_intel_admin as ria
import routes_market_intel as ri
from kaos_rate_limit import SlidingWindowLimiter

USER = {"id": "member-a", "email": "a@example.com", "role": "user", "membership_status": "ACTIVE"}
NOW = datetime(2026, 10, 18, 15, 0, tzinfo=timezone.utc)
BASE = int((NOW - timedelta(minutes=26)).timestamp() * 1000)


def matches(row, query):
    for key, expected in query.items():
        actual = row.get(key)
        if isinstance(expected, dict):
            if "$gte" in expected and not (actual or "") >= expected["$gte"]:
                return False
            if "$or" in expected:
                continue
        elif actual != expected:
            return False
    return True


class FakeCursor:
    def __init__(self, rows):
        self.rows = list(rows)

    def sort(self, key, direction=-1):
        self.rows.sort(key=lambda r: r.get(key) or "", reverse=(direction == -1))
        return self

    def limit(self, count):
        self.rows = self.rows[:count]
        return self

    async def to_list(self, length):
        return self.rows[:length]


class FakeCollection:
    def __init__(self):
        self.rows = []

    async def insert_one(self, doc):
        self.rows.append(dict(doc))
        return SimpleNamespace(inserted_id=doc.get("id"))

    async def find_one(self, query, projection=None, sort=None):
        rows = [r for r in self.rows if matches(r, query)]
        if sort:
            key, direction = sort[0]
            rows.sort(key=lambda r: r.get(key) or "", reverse=(direction == -1))
        return dict(rows[0]) if rows else None

    def find(self, query, projection=None):
        return FakeCursor(dict(r) for r in self.rows if matches(r, query))

    async def count_documents(self, query):
        return sum(1 for r in self.rows if matches(r, query))

    async def update_one(self, query, update, upsert=False):
        rows = [r for r in self.rows if matches(r, query)]
        if not rows:
            if upsert:
                self.rows.append({**query, **update.get("$set", {})})
            return SimpleNamespace(modified_count=0)
        row = rows[0]
        for operator, fields in update.items():
            if operator == "$set":
                row.update(fields)
            elif operator == "$addToSet":
                for key, value in fields.items():
                    values = row.setdefault(key, [])
                    if value not in values:
                        values.append(value)
            elif operator == "$pull":
                for key, value in fields.items():
                    row[key] = [x for x in (row.get(key) or []) if x != value]
        return SimpleNamespace(modified_count=1)

    async def delete_one(self, query):
        rows = [r for r in self.rows if matches(r, query)]
        if not rows:
            return SimpleNamespace(deleted_count=0)
        self.rows.remove(rows[0])
        return SimpleNamespace(deleted_count=1)


class FakeDB:
    def __init__(self):
        self._collections = {}

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return self._collections.setdefault(name, FakeCollection())


def candles(ts_base=BASE):
    out = []
    for i in range(25):
        out.append({"time": (ts_base // 1000) + i * 60, "open": 100.0, "high": 100.2,
                    "low": 99.8, "close": 100.0, "volume": 10.0})
    out.append({"time": (ts_base // 1000) + 25 * 60, "open": 100.1, "high": 102.2,
                "low": 100.0, "close": 102.0, "volume": 40.0})
    return out


@pytest.fixture
def env(monkeypatch):
    database = FakeDB()
    monkeypatch.setattr(ri, "db", database)
    monkeypatch.setattr(ria, "db", database)
    monkeypatch.setattr(ri, "now", lambda: NOW)
    monkeypatch.setattr(ri, "now_iso", lambda: NOW.isoformat())
    monkeypatch.setattr(ri, "get_entitlements", AsyncMock(return_value={"scanners": True, "tier": "pro"}))
    monkeypatch.setattr(ri, "notify", AsyncMock())
    monkeypatch.setattr(ri, "get_setting", AsyncMock(return_value={}))
    monkeypatch.setattr(ria, "get_setting", AsyncMock(return_value={}))
    monkeypatch.setattr(ria, "set_setting", AsyncMock())
    monkeypatch.setattr(ria, "audit_log", AsyncMock())
    ri.SCAN_LIMITER = SlidingWindowLimiter(12, 60)
    ri.WRITE_LIMITER = SlidingWindowLimiter(60, 60)

    async def fake_candles(symbol, asset_class, granularity=60):
        return {"symbol": symbol, "granularity": granularity, "source": "coinbase_exchange_public_ticker",
                "fetched_at": NOW.isoformat(), "candles": candles()}

    monkeypatch.setattr(ri.market_data, "get_candles", fake_candles)
    app = FastAPI()
    app.include_router(ri.router)
    app.include_router(ria.router)
    app.dependency_overrides[ri.member] = lambda: USER
    app.dependency_overrides[ri.get_current_user] = lambda: USER
    app.dependency_overrides[ria.admin_dep] = lambda: {**USER, "role": "admin"}
    return SimpleNamespace(app=app, db=database, client=TestClient(app), monkeypatch=monkeypatch)


def test_entitlement_guard_blocks_free_members(env):
    env.monkeypatch.setattr(ri, "get_entitlements", AsyncMock(return_value={"scanners": False, "tier": "free"}))
    with pytest.raises(HTTPException) as err:
        import asyncio
        asyncio.run(ri.member(user=USER))
    assert err.value.status_code == 403
    assert "Pro" in err.value.detail


def test_catalog_reports_real_availability(env):
    env.monkeypatch.delenv("APCA_API_KEY_ID", raising=False)
    body = env.client.get("/api/v1/intelligence/center/catalog").json()
    modules = {m["key"]: m for m in body["modules"]}
    assert body["research_only"] is True and body["execution_enabled"] is False
    assert modules["crypto"]["data_status"] == "live_public_feed"
    assert modules["stocks"]["data_status"] == "provider_not_configured"
    assert "APCA_API_KEY_ID" in modules["stocks"]["required_env"]


def test_crypto_scan_returns_provenance_and_rejects_bad_symbols(env):
    response = env.client.get("/api/v1/intelligence/scanners/crypto?symbols=BTC-USD,ETH-USD")
    assert response.status_code == 200
    body = response.json()
    assert body["data_status"] == "live" and body["research_only"] is True
    assert {r["symbol"] for r in body["rows"]} == {"BTC-USD", "ETH-USD"}
    row = body["rows"][0]
    assert row["structure"] == "breakout"
    assert row["as_of"] and row["freshness"] == "recent"
    assert body["source"] and body["fetched_at"] and body["coverage_note"]
    assert row["score_type"] == "heuristic_attention_rank_not_probability"

    assert env.client.get("/api/v1/intelligence/scanners/crypto?symbols=FAKE-USD").status_code == 422
    assert env.client.get("/api/v1/intelligence/scanners/crypto?granularity=30").status_code == 422


def test_crypto_scan_never_invents_rows_when_provider_fails(env):
    async def broken(symbol, asset_class, granularity=60):
        raise ri.market_data.QuoteUnavailable("Market data provider unreachable")

    env.monkeypatch.setattr(ri.market_data, "get_candles", broken)
    body = env.client.get("/api/v1/intelligence/scanners/crypto").json()
    assert body["rows"] == []
    assert body["data_status"] == "provider_unavailable"
    assert any("unreachable" in e["reason"] for e in body["errors"])


def test_stock_scan_is_honest_when_provider_is_not_configured(env):
    env.monkeypatch.delenv("APCA_API_KEY_ID", raising=False)
    env.monkeypatch.delenv("APCA_API_SECRET_KEY", raising=False)
    body = env.client.get("/api/v1/intelligence/scanners/stocks").json()
    assert body["data_status"] == "provider_not_configured"
    assert body["rows"] == []
    assert body["required_env"] == ["APCA_API_KEY_ID", "APCA_API_SECRET_KEY"]


def test_stock_scan_scores_configured_provider_candles(env):
    env.monkeypatch.setenv("APCA_API_KEY_ID", "key")
    env.monkeypatch.setenv("APCA_API_SECRET_KEY", "secret")

    async def fake_stock(symbols, minutes=180):
        return {"source": "alpaca_market_data", "feed": "iex", "fetched_at": NOW.isoformat(),
                "coverage_note": "IEX is a single exchange",
                "candles": {s: [{"ts": BASE + i * 60000, "open": 100.0, "high": 100.2,
                                 "low": 99.8, "close": 100.0, "volume": 10.0} for i in range(25)]
                            for s in symbols}}

    env.monkeypatch.setattr(ri.market_data, "get_stock_candles", fake_stock)
    body = env.client.get("/api/v1/intelligence/scanners/stocks?symbols=AAPL").json()
    assert body["data_status"] == "live"
    assert body["rows"][0]["symbol"] == "AAPL"
    assert body["feed"] == "iex" and "single exchange" in body["coverage_note"]


def test_social_scan_aggregates_stored_observations_only(env):
    for i in range(3):
        env.db.kaos_intelligence.rows.append({
            "asset": "AAA", "asset_class": "stock", "source": "social", "direction": "neutral",
            "strength": 0.2, "event_id": f"bsky-search:AAA:{i}",
            "observed_at": (NOW - timedelta(minutes=10)).isoformat(),
            "published_at": (NOW - timedelta(minutes=11)).isoformat(),
            "source_url": "https://bsky.app/profile/a/post/1"})
    body = env.client.get("/api/v1/intelligence/scanners/social").json()
    assert body["data_status"] == "ingested_observations"
    assert body["rows"][0]["asset"] == "AAA"
    assert body["rows"][0]["velocity"] == "new"
    assert "not the whole" in body["coverage_note"]


def test_social_scan_reports_empty_state_without_fabrication(env):
    body = env.client.get("/api/v1/intelligence/scanners/social").json()
    assert body["data_status"] == "no_ingested_observations"
    assert body["rows"] == []
    assert body["collector_configured"] is False


def test_options_research_exposes_only_stored_metrics(env):
    expiry = NOW.strftime("%y%m%d")
    env.db.kaos_intelligence.rows.append({
        "asset": f"SPY{expiry}C00500000", "asset_class": "option", "source": "options_flow",
        "direction": "neutral", "strength": 0.5, "event_id": "option-volume-rise:0:SPY:1",
        "observed_at": (NOW - timedelta(minutes=5)).isoformat(),
        "published_at": (NOW - timedelta(minutes=5)).isoformat(),
        "source_url": "https://docs.tradier.com/reference", "summary": "volume grew"})
    body = env.client.get("/api/v1/intelligence/options/research?underlying=spy").json()
    assert body["data_status"] == "ingested_observations"
    assert body["spy_0dte_available"] is True
    assert body["rows"][0]["same_day_expiration"] is True
    assert "delta" in body["metrics_unavailable"]
    assert body["provider_configured"] is False


def test_watchlists_are_member_scoped_and_limited(env):
    created = env.client.post("/api/v1/intelligence/watchlists", json={"name": "Momentum"})
    assert created.status_code == 201
    wid = created.json()["id"]
    added = env.client.post(f"/api/v1/intelligence/watchlists/{wid}/symbols", json={"symbol": "btc-usd"})
    assert added.json()["symbols"] == ["BTC-USD"]

    # Another member cannot see or modify it.
    other = {**USER, "id": "member-b"}
    env.app.dependency_overrides[ri.get_current_user] = lambda: other
    assert env.client.get("/api/v1/intelligence/watchlists").json()["watchlists"] == []
    assert env.client.post(f"/api/v1/intelligence/watchlists/{wid}/symbols",
                           json={"symbol": "ETH-USD"}).status_code == 404
    assert env.client.delete(f"/api/v1/intelligence/watchlists/{wid}").status_code == 404

    env.app.dependency_overrides[ri.get_current_user] = lambda: USER
    env.monkeypatch.setattr(ri, "get_entitlements", AsyncMock(return_value={"scanners": True, "tier": "free"}))
    assert env.client.post("/api/v1/intelligence/watchlists", json={"name": "  "}).status_code == 422
    assert env.client.post("/api/v1/intelligence/watchlists", json={"name": "Second"}).status_code == 201
    third = env.client.post("/api/v1/intelligence/watchlists", json={"name": "Third"})
    assert third.status_code == 403 and "2 watchlists" in third.json()["detail"]


def test_alert_validation_and_triggers(env):
    assert env.client.post("/api/v1/intelligence/alerts",
                           json={"name": "bad", "kind": "price_above", "symbol": "BTC-USD"}).status_code == 422
    created = env.client.post("/api/v1/intelligence/alerts",
                              json={"name": "Breakout", "kind": "breakout_20", "symbol": "BTC-USD"})
    assert created.status_code == 201
    body = env.client.post("/api/v1/intelligence/alerts/evaluate").json()
    assert body["evaluated"] == 1
    assert body["triggered"][0]["symbol"] == "BTC-USD"
    ri.notify.assert_awaited_once()

    # The same alert does not spam a new notification within the hour.
    env.client.post("/api/v1/intelligence/alerts/evaluate")
    assert ri.notify.await_count == 1

    assert env.client.delete(f"/api/v1/intelligence/alerts/{created.json()['id']}").status_code == 200


def test_alert_limit_and_evaluate_without_alerts(env):
    body = env.client.post("/api/v1/intelligence/alerts/evaluate").json()
    assert body["evaluated"] == 0 and body["triggered"] == []
    env.db.member_alerts.rows.extend([
        {"id": f"a{i}", "user_id": "member-a", "name": f"a{i}", "kind": "breakout_20"}
        for i in range(ri.MAX_ALERTS)])
    assert env.client.post("/api/v1/intelligence/alerts",
                           json={"name": "extra", "kind": "breakout_20"}).status_code == 403


def test_scan_rate_limit_returns_429(env):
    ri.SCAN_LIMITER = SlidingWindowLimiter(1, 60)
    assert env.client.get("/api/v1/intelligence/scanners/crypto").status_code == 200
    limited = env.client.get("/api/v1/intelligence/scanners/crypto")
    assert limited.status_code == 429
    assert int(limited.headers["Retry-After"]) >= 1


def test_admin_sources_registry_exposes_presence_not_values(env):
    env.monkeypatch.setenv("APCA_API_KEY_ID", "present-key")
    env.monkeypatch.delenv("APCA_API_SECRET_KEY", raising=False)
    env.db.kaos_intelligence.rows.append({
        "asset": "AAA", "asset_class": "stock", "source": "social", "event_id": "bsky-search:AAA:1",
        "observed_at": (NOW - timedelta(minutes=3)).isoformat(), "observed_at_label": "x"})
    body = env.client.get("/api/admin/intelligence/sources").json()
    alpaca = next(s for s in body["sources"] if s["provider"] == "alpaca")
    assert alpaca["configured"] is False
    assert alpaca["missing_env"] == ["APCA_API_SECRET_KEY"]
    assert "present-key" not in str(body)
    assert body["credentials_exposed"] is False
    assert body["allows_paid_providers"] is False

    toggled = env.client.put("/api/admin/intelligence/sources/alpaca", json={"enabled": False}).json()
    assert toggled["enabled"] is False
    ria.set_setting.assert_awaited_once()
    ria.audit_log.assert_awaited_once()
    assert env.client.put("/api/admin/intelligence/sources/nope", json={"enabled": False}).status_code == 404
