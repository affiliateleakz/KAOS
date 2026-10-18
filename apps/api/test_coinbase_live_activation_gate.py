"""Hard gate regression tests: no implicit real-money activation by merging code."""
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
import routes_coinbase as orders

class Request:
    headers={"authorization":"Bearer test-token"}

def run(coro):
    return asyncio.run(coro)

@pytest.mark.parametrize("flag", [None, "", "disabled", "true", "ENABLED"])
def test_live_orders_fail_closed_without_exact_flag(monkeypatch,flag):
    if flag is None:
        monkeypatch.delenv("KAOS_COINBASE_LIVE_ORDERS", raising=False)
    else:
        monkeypatch.setenv("KAOS_COINBASE_LIVE_ORDERS",flag)
    monkeypatch.setattr(orders,"get_entitlements",AsyncMock(return_value={"botAccess":True}))
    user={"id":"test","membership_status":"ACTIVE","account_status":"active"}
    with pytest.raises(HTTPException) as err:
        run(orders.authorized(Request(),user))
    assert err.value.status_code==403
    assert "disabled" in str(err.value.detail).lower()

def test_enabled_flag_still_requires_live_consent(monkeypatch):
    monkeypatch.setenv("KAOS_COINBASE_LIVE_ORDERS","enabled")
    monkeypatch.setattr(orders,"get_entitlements",AsyncMock(return_value={"botAccess":True}))
    class Consents:
        async def find_one(self,*args,**kwargs):
            return None
    class Database:
        coinbase_live_consent=Consents()
    monkeypatch.setattr(orders,"db",Database())
    user={"id":"test","membership_status":"ACTIVE","account_status":"active"}
    with pytest.raises(HTTPException) as err:
        run(orders.authorized(Request(),user))
    assert err.value.status_code==403
    assert "consent" in str(err.value.detail).lower()
