import asyncio
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
import routes_stock_heatmap as stocks

def test_snapshot_compares_real_previous_close():
    v=stocks.parse_snapshot("AAPL",{"dailyBar":{"c":110,"v":12000,"t":"2026-10-16T20:00:00Z"},"prevDailyBar":{"c":100}})
    assert v["change_pct"]==10
    assert v["volume"]==12000

def test_missing_close_does_not_fabricate_percentage():
    v=stocks.parse_snapshot("AAPL",{"dailyBar":{"c":110},"prevDailyBar":{}})
    assert v["change_pct"] is None

def test_alpaca_only_mode_requires_credentials(monkeypatch):
    monkeypatch.delenv("APCA_API_KEY_ID",raising=False)
    monkeypatch.delenv("APCA_API_SECRET_KEY",raising=False)
    monkeypatch.setenv("KAOS_STOCK_HEATMAP_FALLBACK","alpaca")
    with pytest.raises(HTTPException) as err:
        stocks.provider_mode()
    assert err.value.status_code==503

def test_fallback_disabled_requires_credentials(monkeypatch):
    monkeypatch.delenv("APCA_API_KEY_ID",raising=False)
    monkeypatch.delenv("APCA_API_SECRET_KEY",raising=False)
    monkeypatch.setenv("KAOS_STOCK_HEATMAP_FALLBACK","off")
    with pytest.raises(HTTPException) as err:
        stocks.provider_mode()
    assert err.value.status_code==503

def test_default_mode_uses_keyless_source_without_alpaca(monkeypatch):
    monkeypatch.delenv("APCA_API_KEY_ID",raising=False)
    monkeypatch.delenv("APCA_API_SECRET_KEY",raising=False)
    monkeypatch.delenv("KAOS_STOCK_HEATMAP_FALLBACK",raising=False)
    assert stocks.provider_mode()=="auto"


def test_rejects_unknown_mode(monkeypatch):
    monkeypatch.setenv("KAOS_STOCK_HEATMAP_FALLBACK","nonsense")
    with pytest.raises(HTTPException) as err:
        stocks.provider_mode()
    assert err.value.status_code==503

def test_entitlement_required(monkeypatch):
    monkeypatch.setattr(stocks,"get_entitlements",AsyncMock(return_value={"scanners":False}))
    with pytest.raises(HTTPException) as err:
        asyncio.run(stocks.require_scanners(user={"id":"free"}))
    assert err.value.status_code==403
