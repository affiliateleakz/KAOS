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
