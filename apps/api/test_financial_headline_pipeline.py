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
    monkeypatch.setenv("KAOS_TRADING_HERO_MODEL_VERSION", "reviewed-test-revision")
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
    monkeypatch.setenv("KAOS_TRADING_HERO_MODEL_VERSION", "reviewed-test-revision")
    monkeypatch.setattr(kaos_financial_inference,"classify_headlines",
        lambda xs:[{"headline":xs[0],"sentiment_score":0.7,"label":"positive","confidence":0.7}])
    save=AsyncMock()
    monkeypatch.setattr(api,"db",SimpleNamespace(
        kaos_intelligence=SimpleNamespace(update_one=save)))
    result=asyncio.run(api.classify_and_ingest_headlines([data()],"secret-for-test"))
    assert result["accepted"] == 1
    assert result["trade_execution_enabled"] is False
    assert save.await_args.args[1]["$setOnInsert"]["nlp_score"] == 0.7


def test_incomplete_model_batch_cannot_be_ingested(monkeypatch):
    monkeypatch.setenv("KAOS_COLLECTOR_KEY", "secret-for-test")
    monkeypatch.setenv("KAOS_TRADING_HERO_MODEL_VERSION", "reviewed-test-revision")
    monkeypatch.setattr(kaos_financial_inference, "classify_headlines",
                        lambda texts: [])
    save = AsyncMock()
    monkeypatch.setattr(api, "db", SimpleNamespace(
        kaos_intelligence=SimpleNamespace(update_one=save)))
    with pytest.raises(HTTPException) as err:
        asyncio.run(api.classify_and_ingest_headlines([data()], "secret-for-test"))
    assert err.value.status_code == 503
    save.assert_not_awaited()


def test_misaligned_model_response_cannot_be_ingested(monkeypatch):
    monkeypatch.setenv("KAOS_COLLECTOR_KEY", "secret-for-test")
    monkeypatch.setattr(kaos_financial_inference, "classify_headlines",
                        lambda texts: [{"headline": "Other company",
                                        "sentiment_score": 0.9}])
    save = AsyncMock()
    monkeypatch.setattr(api, "db", SimpleNamespace(
        kaos_intelligence=SimpleNamespace(update_one=save)))
    with pytest.raises(HTTPException) as err:
        asyncio.run(api.classify_and_ingest_headlines([data()], "secret-for-test"))
    assert err.value.status_code == 503
    save.assert_not_awaited()


def test_same_headline_from_two_models_retains_separate_provenance(monkeypatch):
    monkeypatch.setenv("KAOS_COLLECTOR_KEY", "secret-for-test")
    save = AsyncMock()
    monkeypatch.setattr(api, "db", SimpleNamespace(
        kaos_intelligence=SimpleNamespace(update_one=save)))
    shared = dict(ticker="SPY", asset_class="etf",
                  headline="Revenue rose above expectations",
                  source_url="https://example.org/earnings",
                  published_at=datetime.now(timezone.utc))
    scored = [api.HeadlineScore(**shared, score=0.8, model_id="model-a",
                                model_version="1"),
              api.HeadlineScore(**shared, score=-0.4, model_id="model-b",
                                model_version="2")]
    result = asyncio.run(api.ingest_headline_scores(scored, "secret-for-test"))
    assert result["accepted"] == 2
    records = [call.args[1]["$setOnInsert"] for call in save.await_args_list]
    assert {r["nlp_model_id"] for r in records} == {"model-a", "model-b"}
    assert len({r["event_id"] for r in records}) == 2
    assert {r["nlp_score"] for r in records} == {0.8, -0.4}


def test_unversioned_model_is_not_allowed_to_persist_predictions(monkeypatch):
    monkeypatch.setenv("KAOS_COLLECTOR_KEY", "secret-for-test")
    monkeypatch.delenv("KAOS_TRADING_HERO_MODEL_VERSION", raising=False)
    save = AsyncMock()
    monkeypatch.setattr(api, "db", SimpleNamespace(
        kaos_intelligence=SimpleNamespace(update_one=save)))
    with pytest.raises(HTTPException) as err:
        asyncio.run(api.classify_and_ingest_headlines([data()], "secret-for-test"))
    assert err.value.status_code == 503
    save.assert_not_awaited()
