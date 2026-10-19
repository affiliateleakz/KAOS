import asyncio
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
import routes_ai_outcomes as api

def item(source="other_provider"):
    return api.CollectorObservation(prediction_id="pred-123",asset="BTC-USD",source=source,
      observed_at="2026-10-18T12:00:01Z",price="101.00")

def test_refuse_unknown_quote_provider(monkeypatch):
    monkeypatch.setenv("KAOS_COLLECTOR_KEY","secret")
    db=type("DB",(),{})()
    db.ai_predictions=type("Collection",(),{"find_one":AsyncMock(return_value={
      "asset":"BTC-USD","productionTrained":True,"simulated":False,"timestamp":"2026-10-18T12:00:00Z"})})()
    monkeypatch.setattr(api,"db",db)
    with pytest.raises(HTTPException) as error:
        asyncio.run(api.record_observations([item()],x_kaos_collector_key="secret"))
    assert error.value.status_code==422

def test_refuse_unknown_prediction(monkeypatch):
    monkeypatch.setenv("KAOS_COLLECTOR_KEY","secret")
    db=type("DB",(),{})()
    db.ai_predictions=type("Collection",(),{"find_one":AsyncMock(return_value=None)})()
    monkeypatch.setattr(api,"db",db)
    with pytest.raises(HTTPException) as error:
        asyncio.run(api.record_observations([item("coinbase_exchange_public_ticker")],x_kaos_collector_key="secret"))
    assert error.value.status_code==422
