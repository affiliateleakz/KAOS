"""Authenticated NLP score ingestion into the existing Opportunity Radar."""
import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
import routes_opportunity as api

NOW = datetime.now(timezone.utc)

def payload(score=0.8):
    return api.HeadlineScore(ticker="SPY", asset_class="etf",
        headline="Earnings expectations have increased",
        source_url="https://example.com/news/1", published_at=NOW,
        score=score, model_id="trading_hero", model_version="test-v1")

def test_ingest_requires_collector_secret(monkeypatch):
    monkeypatch.setenv("KAOS_COLLECTOR_KEY","test-only-collector-secret")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(api.ingest_headline_scores([payload()],None))
    assert exc.value.status_code == 403

def test_ingested_sentiment_is_research_only_and_attributed(monkeypatch):
    monkeypatch.setenv("KAOS_COLLECTOR_KEY","test-only-collector-secret")
    records=[]
    async def save(query, update, upsert):
        records.append((query,update))
    monkeypatch.setattr(api, "db",SimpleNamespace(
        kaos_intelligence=SimpleNamespace(update_one=save)))
    result=asyncio.run(api.ingest_headline_scores(
        [payload()], "test-only-collector-secret"))
    assert result["accepted"] == 1
    assert result["trade_execution_enabled"] is False
    record=records[0][1]["$setOnInsert"]
    assert record["nlp_model_id"] == "trading_hero"
    assert record["direction"] == "bullish"
    assert record["research_only"] is True
    assert records[0][0]["event_id"].startswith("nlp:")
