"""Persistent KAOS R2 Train AI job contract and fail-closed coverage tests."""
import asyncio
from datetime import datetime,timezone
import pytest
import kaos_ai_training_jobs as jobs

def test_train_all_covers_configured_r2_markets_not_fictitious_options():
    job=jobs.initial_job("owner","all","BTC-USD",5000,4)
    assert job["status"]=="queued"
    assert job["total"]==len(jobs.MARKETS)
    assert job["total"]>1
    assert {"stock","crypto","etf"} <= {m["asset_class"] for m in job["markets"]}
    assert "option" not in {m["asset_class"] for m in job["markets"]}
    assert job["research_only"] is True
    assert job["execution_enabled"] is False
    assert job["next_index"]==0
    assert job["results"]==[]

def test_train_one_only_uses_supported_market():
    job=jobs.initial_job("owner","single","AAPL",300,2)
    assert job["total"]==1
    assert job["markets"][0]=={"symbol":"AAPL","asset_class":"stock"}
    with pytest.raises(ValueError):
        jobs.initial_job("owner","single","FAKE-OPTION",300,2)
    with pytest.raises(ValueError):
        jobs.initial_job("owner","all","BTC-USD",5001,2)
    with pytest.raises(ValueError):
        jobs.initial_job("owner","all","BTC-USD",5000,31)

def test_training_source_manifest_does_not_claim_news_social_or_insiders():
    ready=jobs.source_report(archive_status="ready",archive_rows=5000,source="alpaca_iex")
    assert {x["key"] for x in ready if x["used_in_training"]}=={
        "r2_ohlcv","candlestick_features"
    }
    for name in ("news","social","insider_trades","institutional_trades",
                 "short_interest","options_flow","macro_events","supply_demand",
                 "pattern_observer"):
        source=next(x for x in ready if x["key"]==name)
        assert source["used_in_training"] is False
        assert source["status"]=="not_integrated"

def test_public_job_does_not_return_private_owner_id_or_lease():
    item=jobs.initial_job("my-private-owner-id","all","BTC-USD",5000,4)
    result=jobs.public_job(item)
    assert result["id"]==item["_id"]
    for secret in ("owner_id","worker_token","lease_until","_id"):
        assert secret not in result
    assert result["orders_enabled"] is False

def test_worker_refuses_disabled_without_touching_database(monkeypatch):
    monkeypatch.delenv("KAOS_R2_TRAIN_WORKER_ENABLED",raising=False)
    result=asyncio.run(jobs.run_tick())
    assert result["status"]=="disabled"

def test_archive_error_is_not_fake_trained_model(monkeypatch):
    class Error(jobs.ArchiveUnavailable): pass
    async def fail(*args,**kwargs):
        raise Error("private secret never copy")
    monkeypatch.setattr(jobs,"read_archive",fail)
    job=jobs.initial_job("owner","single","AAPL",5000,4)
    result=asyncio.run(jobs.train_one_market(job,{"symbol":"AAPL","asset_class":"stock"}))
    assert result["status"]=="source_error"
    assert result["reason"]=="Error"
    assert "private secret" not in str(result)
    assert not any(x["used_in_training"] for x in result["training_sources"])

def test_unchanged_low_history_not_invented_training(monkeypatch):
    async def archive(*args,**kwargs):
        return ([{"ts":i*60000} for i in range(150)],"coinbase_exchange_public")
    monkeypatch.setattr(jobs,"read_archive",archive)
    job=jobs.initial_job("owner","single","BTC-USD",300,4)
    result=asyncio.run(jobs.train_one_market(job,job["markets"][0]))
    assert result["status"]=="insufficient_history"
    assert result["rows"]==150
    assert result.get("model_id") is None

def test_worker_manifest_is_research_only_without_any_order_tools():
    job=jobs.initial_job("owner","single","AAPL",5000,4)
    assert job["other_sources_enabled"] is False
    assert job["model_family"]=="kaos_r2_ohlc_logistic_v1"
    assert job["trained_feature_names"]==list(jobs.TRAINED_FEATURES)
