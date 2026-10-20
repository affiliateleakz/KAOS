import asyncio
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
import routes_ai_outcomes as api

def test_collector_requires_key(monkeypatch):
    monkeypatch.setenv("KAOS_COLLECTOR_KEY","secret")
    with pytest.raises(HTTPException) as err:
        asyncio.run(api.record_observations([],x_kaos_collector_key="invalid"))
    assert err.value.status_code==403

def test_settlement_rejects_unknown_prediction(monkeypatch):
    class MockDB:
        ai_predictions=type("Predictions",(),{"find_one":AsyncMock(return_value=None)})()
    monkeypatch.setattr(api,"db",MockDB())
    with pytest.raises(HTTPException) as err:
        asyncio.run(api.settle_verified(api.SettleRequest(prediction_id="pred-123",horizon_seconds=30),admin={"id":"admin"}))
    assert err.value.status_code==404


def test_collector_rejects_future_quote_without_writing(monkeypatch):
    from datetime import datetime, timezone, timedelta
    from types import SimpleNamespace
    monkeypatch.setenv("KAOS_COLLECTOR_KEY", "secret")
    update = AsyncMock()
    monkeypatch.setattr(api, "db", SimpleNamespace(
        kaos_ai_quote_observations=SimpleNamespace(update_one=update)))
    future = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
    item = api.CollectorObservation(
        prediction_id="pred-123", asset="BTC-USD", source="coinbase",
        observed_at=future, price="100")
    with pytest.raises(HTTPException) as err:
        asyncio.run(api.record_observations([item], "secret"))
    assert err.value.status_code == 422
    update.assert_not_awaited()


def test_collector_rejects_stale_quote_without_writing(monkeypatch):
    from datetime import datetime, timezone, timedelta
    from types import SimpleNamespace
    monkeypatch.setenv("KAOS_COLLECTOR_KEY", "secret")
    update = AsyncMock()
    monkeypatch.setattr(api, "db", SimpleNamespace(
        kaos_ai_quote_observations=SimpleNamespace(update_one=update)))
    stale = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
    item = api.CollectorObservation(
        prediction_id="pred-123", asset="BTC-USD", source="coinbase",
        observed_at=stale, price="100")
    with pytest.raises(HTTPException) as err:
        asyncio.run(api.record_observations([item], "secret"))
    assert err.value.status_code == 422
    update.assert_not_awaited()
