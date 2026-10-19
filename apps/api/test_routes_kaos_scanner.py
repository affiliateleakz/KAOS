"""Public preview must never turn client statements into verified signals."""
import asyncio
from datetime import datetime, timezone
import pytest
from fastapi import HTTPException
from routes_kaos_scanner import Evidence, ScanInput, scan_preview

def test_preview_is_not_executable():
    ts=datetime.now(timezone.utc)
    req=ScanInput(broker="alpaca", assets={"SPY":[
        Evidence(source="strategy",asset="SPY",direction="BUY",timestamp=ts),
        Evidence(source="chart",asset="SPY",direction="BUY",timestamp=ts)]})
    result=asyncio.run(scan_preview(req, {"id":"test-user"}))
    assert result["executable"] is False
    assert result["opportunities"][0]["status"] == "NO_TRADE"
    assert all(x["reason"] == "unverified_or_simulated"
               for x in result["opportunities"][0]["excluded_evidence"])

def test_preview_rejects_suspended_accounts():
    req=ScanInput(broker="alpaca",assets={"SPY":[]})
    with pytest.raises(HTTPException) as e:
        asyncio.run(scan_preview(req, {"id":"u1","account_status":"suspended"}))
    assert e.value.status_code == 403

from types import SimpleNamespace
from unittest.mock import AsyncMock
import routes_kaos_scanner as scanner


def test_collected_scan_rejects_unentitled_member(monkeypatch):
    monkeypatch.setattr(scanner, "get_entitlements",
                        AsyncMock(return_value={"scanners":False}))
    with pytest.raises(HTTPException) as exc:
        asyncio.run(scanner.collected_opportunities(user={"id":"user1"}))
    assert exc.value.status_code == 403


def test_collected_scan_uses_only_server_stored_evidence(monkeypatch):
    class Cursor:
        def sort(self, *_): return self
        def limit(self, *_): return self
        async def to_list(self, **kwargs):
            return [{"asset":"SPY","asset_class":"stock","source":"technical",
                     "direction":"bullish","strength":0.7}]
    collection=SimpleNamespace(find=lambda *a, **k: Cursor())
    monkeypatch.setattr(scanner,"db",SimpleNamespace(kaos_intelligence=collection))
    monkeypatch.setattr(scanner,"get_entitlements",
                        AsyncMock(return_value={"scanners":True}))
    monkeypatch.setattr(scanner,"evaluate",
                        lambda asset, rows: {"asset":asset,"score":0.4})
    result=asyncio.run(scanner.collected_opportunities(user={"id":"user1"}))
    assert result["mode"] == "COLLECTOR_RESEARCH"
    assert result["executable"] is False
    assert result["opportunities"][0]["asset"] == "SPY"
