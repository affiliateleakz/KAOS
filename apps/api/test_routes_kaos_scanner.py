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
