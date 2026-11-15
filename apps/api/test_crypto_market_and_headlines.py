"""Tests for the keyless crypto bubble feed and the free headline feed."""
import asyncio

import pytest
from fastapi import HTTPException

import routes_crypto_scanner as crypto
import routes_disclosures as disclosures


def run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def clear_caches():
    crypto._MARKET_CACHE.update(at=0.0, payload=None, provider=None)
    disclosures._HEADLINE_CACHE.clear()
    yield
    crypto._MARKET_CACHE.update(at=0.0, payload=None, provider=None)
    disclosures._HEADLINE_CACHE.clear()


COINGECKO_ROWS = [
    {"symbol": "BTC", "name": "Bitcoin", "price_usd": 95000.0, "market_cap": 1.9e12,
     "volume_24h": 4.0e10, "change_1h": 0.2, "change_24h": 1.8, "change_7d": -3.1,
     "image": "https://assets.coingecko.com/coins/images/1/large/bitcoin.png",
     "url": "https://www.coingecko.com/en/coins/bitcoin", "source": "CoinGecko"},
    {"symbol": "ETH", "name": "Ethereum", "price_usd": 3200.0, "market_cap": 3.8e11,
     "volume_24h": 1.5e10, "change_1h": -0.1, "change_24h": -2.4, "change_7d": 4.0,
     "image": None, "url": "https://www.coingecko.com/en/coins/ethereum", "source": "CoinGecko"},
]

COINBASE_ROWS = [
    {"symbol": "BTC", "name": "BTC", "price_usd": 94000.0, "market_cap": None,
     "volume_24h": 2.0e10, "change_1h": None, "change_7d": None, "change_24h": -1.0,
     "image": None, "url": "https://www.coinbase.com/price/btc", "source": "Coinbase"},
]


def test_market_prefers_coingecko_and_flags_research_only(monkeypatch):
    async def fake(limit):
        assert limit == 60
        return list(COINGECKO_ROWS)

    monkeypatch.setattr(crypto, "_coingecko_market", fake)
    out = run(crypto.crypto_market(60, user={"user_id": "tester"}))

    assert out["provider"].startswith("CoinGecko")
    assert out["weighting"] == "market_cap"
    assert out["count"] == 2
    assert out["cached"] is False
    assert out["research_only"] is True
    assert out["trade_execution_enabled"] is False
    assert out["coins"][0]["symbol"] == "BTC"
    assert out["failures"] == []


def test_coin_row_normalizes_raw_provider_fields():
    row = crypto._coin_row({"symbol": "sol", "name": "Solana", "current_price": 210.5,
                            "market_cap": 1.1e11, "total_volume": 6.0e9,
                            "price_change_percentage_1h_in_currency": 0.4,
                            "price_change_percentage_24h_in_currency": -1.6,
                            "price_change_percentage_7d_in_currency": 8.2,
                            "image": "http://insecure.example/sol.png", "id": "solana"})

    assert row["symbol"] == "SOL"
    assert row["change_24h"] == -1.6
    assert row["image"] is None  # non-https images are dropped
    assert "insecure" not in row["url"]
    assert row["url"] == "https://www.coingecko.com/en/coins/solana"


def test_coin_row_falls_back_to_plain_24h_change():
    row = crypto._coin_row({"symbol": "ada", "current_price": 1.0,
                            "price_change_percentage_24h": -4.25})
    assert row["change_24h"] == -4.25
    assert row["change_1h"] is None
    assert row["change_7d"] is None


def test_market_serves_cache_on_second_request(monkeypatch):
    calls = {"n": 0}

    async def fake(limit):
        calls["n"] += 1
        return list(COINGECKO_ROWS)

    monkeypatch.setattr(crypto, "_coingecko_market", fake)
    first = run(crypto.crypto_market(60, user={"user_id": "tester"}))
    second = run(crypto.crypto_market(60, user={"user_id": "tester"}))

    assert calls["n"] == 1
    assert first["cached"] is False
    assert second["cached"] is True
    assert second["count"] == first["count"]


def test_market_falls_back_to_coinbase_volume_weighting(monkeypatch):
    async def failing(limit):
        raise RuntimeError("coinGecko down")

    async def fallback(limit, semaphore):
        return list(COINBASE_ROWS)

    monkeypatch.setattr(crypto, "_coingecko_market", failing)
    monkeypatch.setattr(crypto, "_coinbase_market", fallback)
    out = run(crypto.crypto_market(60, user={"user_id": "tester"}))

    assert out["provider"].startswith("Coinbase")
    assert out["weighting"] == "24h_volume"
    assert out["failures"] == ["coingecko"]
    assert out["coins"][0]["source"] == "Coinbase"


def test_market_raises_503_when_every_provider_fails(monkeypatch):
    async def failing(limit):
        raise RuntimeError("down")

    async def failing_fallback(limit, semaphore):
        raise RuntimeError("down too")

    monkeypatch.setattr(crypto, "_coingecko_market", failing)
    monkeypatch.setattr(crypto, "_coinbase_market", failing_fallback)

    with pytest.raises(HTTPException) as err:
        run(crypto.crypto_market(60, user={"user_id": "tester"}))
    assert err.value.status_code == 503


def test_market_serves_recent_stale_snapshot_instead_of_error(monkeypatch):
    async def failing(limit):
        raise RuntimeError("down")

    async def failing_fallback(limit, semaphore):
        raise RuntimeError("down too")

    payload = {"coins": list(COINGECKO_ROWS), "count": 2, "provider": "CoinGecko (free, no key)",
               "weighting": "market_cap", "failures": [], "research_only": True,
               "trade_execution_enabled": False, "warning": "snapshot"}
    crypto._MARKET_CACHE.update(at=crypto.time.monotonic() - 120, payload=payload, provider=payload["provider"])
    monkeypatch.setattr(crypto, "_coingecko_market", failing)
    monkeypatch.setattr(crypto, "_coinbase_market", failing_fallback)

    out = run(crypto.crypto_market(60, user={"user_id": "tester"}))
    assert out["cached"] is True
    assert out["stale"] is True
    assert out["count"] == 2


HEADLINE_XML = b"""<?xml version="1.0"?>
<rss version="2.0"><channel>
  <item>
    <title>Senate panel advances market structure bill</title>
    <link>https://news.google.com/rss/articles/abc123</link>
    <source>Reuters</source>
    <pubDate>Sun, 15 Nov 2026 09:00:00 GMT</pubDate>
  </item>
  <item>
    <title>Off-host lookalike link</title>
    <link>https://evil.example/phish</link>
    <source>Unknown</source>
  </item>
  <item>
    <title></title>
    <link>https://news.google.com/rss/articles/empty-title</link>
    <source>Nobody</source>
  </item>
  <item>
    <title>Fund flows turn positive into year end</title>
    <link>https://finance.yahoo.com/news/fund-flows-123.html</link>
    <source>Yahoo Finance</source>
  </item>
</channel></rss>"""


def test_headline_parser_drops_off_host_and_empty_titles():
    rows = disclosures._parse_headlines(HEADLINE_XML, "politics")
    assert [r["publisher"] for r in rows] == ["Reuters", "Yahoo Finance"]
    assert all(r["url"].startswith("https://") for r in rows)
    assert rows[0]["topic"] == "politics"
    assert len(rows[0]["title"]) <= 300


def test_headline_parser_rejects_oversized_payload():
    with pytest.raises(ValueError):
        disclosures._parse_headlines(b"x" * 2_000_001, "politics")


def test_headlines_reject_unknown_topic():
    with pytest.raises(HTTPException) as err:
        run(disclosures.free_headlines("sports", user={"user_id": "tester"}))
    assert err.value.status_code == 422


def test_headlines_use_cache_without_network(monkeypatch):
    class Boom:
        def __init__(self, *a, **kw):
            raise AssertionError("network must not be touched on a cache hit")

    monkeypatch.setattr(disclosures.httpx, "AsyncClient", Boom)
    payload = {"topic": "wallstreet", "headlines": [{"title": "Cached headline", "url": "https://news.google.com/x",
               "publisher": "Reuters", "published_at": "", "topic": "wallstreet"}],
               "count": 1, "provider": "Google News RSS (free, no key)", "research_only": True, "note": ""}
    disclosures._HEADLINE_CACHE["wallstreet"] = (disclosures.time.monotonic(), payload)

    out = run(disclosures.free_headlines("wallstreet", user={"user_id": "tester"}))
    assert out["cached"] is True
    assert out["count"] == 1
    assert out["headlines"][0]["title"] == "Cached headline"


def test_bubble_periods_preserve_zero_and_do_not_invent_missing_returns():
    row = crypto._coin_row({"symbol": "btc", "current_price": 1,
                            "price_change_percentage_24h_in_currency": 0,
                            "price_change_percentage_24h": 5,
                            "price_change_percentage_30d_in_currency": -12.5,
                            "price_change_percentage_1y_in_currency": 25.0})
    assert row["change_24h"] == 0
    assert row["change_30d"] == -12.5
    assert row["change_1y"] == 25.0
    assert row["change_1h"] is None
    assert row["change_7d"] is None
