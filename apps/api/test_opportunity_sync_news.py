import asyncio
import re
import time
import types
from datetime import datetime, timezone, timedelta

import pytest
from fastapi import HTTPException

import routes_opportunity as radar


class FakeCollection:
    def __init__(self):
        self.upserts = []

    async def update_one(self, selector, update, upsert=False):
        self.upserts.append((selector, update, upsert))


class FakeDB:
    def __init__(self):
        self.kaos_intelligence = FakeCollection()


@pytest.fixture(autouse=True)
def reset_sync_state():
    radar._NEWS_SYNC_SEEN.clear()
    radar._GDELT_DOWN_UNTIL = 0.0
    yield
    radar._NEWS_SYNC_SEEN.clear()
    radar._GDELT_DOWN_UNTIL = 0.0


def fake_module(articles):
    mod = types.SimpleNamespace()
    mod.SYMBOL_RE = re.compile(r"^[A-Z][A-Z0-9.]{0,11}$")
    mod.QUERY_RE = re.compile(r'^[\w\s\-.,():"/$&|]+$')
    calls = {"fetched": 0}

    def fetch_articles(query, **kwargs):
        calls["fetched"] += 1
        return articles

    def observe_articles(symbol, query, items, now=None, *, max_items=12):
        out = []
        for item in items:
            out.append({"asset": symbol, "asset_class": "stock", "source": "news",
                        "direction": "neutral", "strength": 0.25,
                        "event_id": "gdelt:" + symbol + ":" + str(len(out)),
                        "observed_at": now.isoformat(),
                        "published_at": (now - timedelta(hours=1)).isoformat(),
                        "source_url": item["url"], "summary": item["title"]})
        return out

    mod.fetch_articles = fetch_articles
    mod.observe_articles = observe_articles
    mod.calls = calls
    return mod


def test_rejects_unsafe_ticker(monkeypatch):
    monkeypatch.setattr(radar, "_gdelt_module", lambda: fake_module([]))
    with pytest.raises(HTTPException) as err:
        asyncio.run(radar.sync_news(symbol="../etc", query=None, user={"id": "u1"}))
    assert err.value.status_code == 422


def test_stores_recent_headlines_and_dedupes(monkeypatch):
    monkeypatch.setattr(radar, "_gdelt_module",
                        lambda: fake_module([{"url": "https://example.com/a", "title": "A"}]))
    db = FakeDB()
    monkeypatch.setattr(radar, "db", db)
    radar._NEWS_SYNC_SEEN.clear()
    result = asyncio.run(radar.sync_news(symbol="aapl", query=None, user={"id": "u2"}))
    assert result["symbol"] == "AAPL"
    assert result["articles_examined"] == 1
    assert result["observations_stored"] == 1
    selector, update, upsert = db.kaos_intelligence.upserts[0]
    assert selector == {"source": "news", "event_id": "gdelt:AAPL:0"}
    assert update["$set"]["asset"] == "AAPL" and upsert is True


def test_cooldown_blocks_immediate_repeat(monkeypatch):
    mod = fake_module([])
    monkeypatch.setattr(radar, "_gdelt_module", lambda: mod)
    monkeypatch.setattr(radar, "db", FakeDB())
    radar._NEWS_SYNC_SEEN.clear()
    asyncio.run(radar.sync_news(symbol="MSFT", query=None, user={"id": "u3"}))
    with pytest.raises(HTTPException) as err:
        asyncio.run(radar.sync_news(symbol="MSFT", query=None, user={"id": "u3"}))
    assert err.value.status_code == 429
    assert mod.calls["fetched"] == 1


def test_rejects_query_the_collector_cannot_send(monkeypatch):
    monkeypatch.setattr(radar, "_gdelt_module", lambda: fake_module([]))
    with pytest.raises(HTTPException) as err:
        asyncio.run(radar.sync_news(symbol="AAPL", query="<script>alert(1)</script>",
                                    user={"id": "u4"}))
    assert err.value.status_code == 422


def test_falls_back_to_headline_feed_when_gdelt_refuses(monkeypatch):
    mod = fake_module([])
    def boom(query, **kwargs):
        raise OSError("HTTP Error 429: Too Many Requests")
    mod.fetch_articles = boom
    monkeypatch.setattr(radar, "_gdelt_module", lambda: mod)
    monkeypatch.setattr(radar, "db", FakeDB())
    radar._NEWS_SYNC_SEEN.clear()
    now = datetime.now(timezone.utc)

    async def headlines(ticker, when):
        return [{"asset": ticker, "asset_class": "stock", "source": "news",
                 "direction": "neutral", "strength": 0.25,
                 "event_id": "yahoo-news:" + ticker + ":x",
                 "observed_at": now.isoformat(),
                 "published_at": (now - timedelta(hours=2)).isoformat(),
                 "source_url": "https://example.com/story", "summary": "headline"}]

    monkeypatch.setattr(radar, "_yahoo_headlines", headlines)
    result = asyncio.run(radar.sync_news(symbol="AAPL", query=None, user={"id": "u5"}))
    assert result["fallback"] is True
    assert result["observations_stored"] == 1
    assert "Yahoo" in result["provider"]


def test_falls_back_when_gdelt_returns_a_non_json_page(monkeypatch):
    """A rate-limit HTML page with HTTP 200 must not surface as a 422 to the member."""
    mod = fake_module([])
    def html_page(query, **kwargs):
        raise ValueError("Expecting value: line 1 column 1 (char 0)")
    mod.fetch_articles = html_page
    monkeypatch.setattr(radar, "_gdelt_module", lambda: mod)
    monkeypatch.setattr(radar, "db", FakeDB())
    radar._NEWS_SYNC_SEEN.clear()
    now = datetime.now(timezone.utc)

    async def headlines(ticker, when):
        return [{"asset": ticker, "asset_class": "stock", "source": "news",
                 "direction": "neutral", "strength": 0.25,
                 "event_id": "yahoo-news:" + ticker + ":html",
                 "observed_at": now.isoformat(),
                 "published_at": (now - timedelta(hours=3)).isoformat(),
                 "source_url": "https://example.com/story", "summary": "headline"}]

    monkeypatch.setattr(radar, "_yahoo_headlines", headlines)
    result = asyncio.run(radar.sync_news(symbol="NVDA", query=None, user={"id": "u6"}))
    assert result["fallback"] is True
    assert result["provider"].startswith("Yahoo")
    assert result["observations_stored"] == 1


def test_gdelt_is_skipped_during_backoff_window(monkeypatch):
    mod = fake_module([])

    def must_not_call(query, **kwargs):
        raise AssertionError("GDELT must not be called during the backoff window")

    mod.fetch_articles = must_not_call
    monkeypatch.setattr(radar, "_gdelt_module", lambda: mod)
    monkeypatch.setattr(radar, "db", FakeDB())
    radar._GDELT_DOWN_UNTIL = time.monotonic() + 300

    async def headlines(ticker, when):
        return []

    monkeypatch.setattr(radar, "_yahoo_headlines", headlines)
    result = asyncio.run(radar.sync_news(symbol="AMD", query=None, user={"id": "u7"}))
    assert result["fallback"] is True
    assert result["provider"].startswith("Yahoo")


def test_real_gdelt_collector_is_importable():
    """The shipped collector module must resolve from the API process."""
    mod = radar._gdelt_module()
    assert hasattr(mod, "fetch_articles") and hasattr(mod, "observe_articles")
