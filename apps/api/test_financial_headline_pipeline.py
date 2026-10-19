"""Collector NLP route requires a genuine model and never guesses on failure."""
import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
import routes_opportunity as api
import kaos_financial_inference

def data():
    return api.UnscoredHeadline(ticker="SPY",asset_class="etf",
        headline="Revenue rose above expectations",
        source_url="https://example.org/earnings",published_at=datetime.now(timezone.utc))

def test_model_not_called_for_unauthorized_collector(monkeypatch):
    monkeypatch.setenv("KAOS_COLLECTOR_KEY","secret-for-test")
    monkeypatch.setattr(kaos_financial_inference,"classify_headlines",
                        lambda *args: (_ for _ in ()).throw(AssertionError("called")))
    with pytest.raises(HTTPException) as err:
        asyncio.run(api.classify_and_ingest_headlines([data()],None))
    assert err.value.status_code == 403

def test_missing_model_rejected_without_fake_result(monkeypatch):
    monkeypatch.setenv("KAOS_COLLECTOR_KEY","secret-for-test")
    def unavailable(*args,**kwargs): raise RuntimeError("model not installed")
    monkeypatch.setattr(kaos_financial_inference,"classify_headlines",unavailable)
    with pytest.raises(HTTPException) as err:
        asyncio.run(api.classify_and_ingest_headlines([data()],"secret-for-test"))
    assert err.value.status_code == 503

def test_real_classifier_output_is_persisted_as_research(monkeypatch):
    monkeypatch.setenv("KAOS_COLLECTOR_KEY","secret-for-test")
    monkeypatch.setattr(kaos_financial_inference,"classify_headlines",
        lambda xs:[{"headline":xs[0],"sentiment_score":0.7,"label":"positive","confidence":0.7}])
    save=AsyncMock()
    monkeypatch.setattr(api,"db",SimpleNamespace(
        kaos_intelligence=SimpleNamespace(update_one=save)))
    result=asyncio.run(api.classify_and_ingest_headlines([data()],"secret-for-test"))
    assert result["accepted"] == 1
    assert result["trade_execution_enabled"] is False
    assert save.await_args.args[1]["$setOnInsert"]["nlp_score"] == 0.7
