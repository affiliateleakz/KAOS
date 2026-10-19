"""Extension license uses the selected broker for broker-specific eligibility."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import routes_extension as ext

def test_coinbase_license_does_not_require_pocket_option_referral(monkeypatch):
    user={"id":"u1","email":"user@example.test","affiliate_status":"NOT_STARTED",
          "membership_status":"ACTIVE","account_status":"active"}
    devices=SimpleNamespace(find_one=AsyncMock(return_value={"id":"d1","userId":"u1","revoked":False}),
                            update_one=AsyncMock())
    brokers=SimpleNamespace(find_one=AsyncMock(return_value={"broker":"coinbase"}))
    monkeypatch.setattr(ext,"db",SimpleNamespace(devices=devices,member_broker_selections=brokers))
    req=SimpleNamespace(headers={"X-Device-Id":"install-1"},
                        client=SimpleNamespace(host="127.0.0.1"))
    license_result=asyncio.run(ext.v1_license(req,user))
    assert license_result["broker"]=="coinbase"
    assert license_result["authorized"] is True
    assert "affiliate_not_verified" not in license_result["reasons"]
