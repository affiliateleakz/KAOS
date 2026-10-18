import asyncio
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
import routes_chart_settings as charts

def run(c): return asyncio.run(c)

def test_free_chart_limit(monkeypatch):
    monkeypatch.setattr(charts, "get_entitlements", AsyncMock(return_value={"chartLimit": 1}))
    assert run(charts._guard({"id": "u"}, 0)) == 1
    with pytest.raises(HTTPException) as err:
        run(charts._guard({"id": "u"}, 1))
    assert err.value.status_code == 403

def test_pro_chart_limit(monkeypatch):
    monkeypatch.setattr(charts, "get_entitlements", AsyncMock(return_value={"chartLimit": 4}))
    assert run(charts._guard({"id": "u"}, 3)) == 4
    with pytest.raises(HTTPException):
        run(charts._guard({"id": "u"}, 4))

def test_timeframes_fail_closed():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        charts.ChartConfig(symbol="BTC-USD", seconds=5)
    with pytest.raises(ValidationError):
        charts.ChartConfig(symbol="BTC-USD", broker="unverified")

def test_upsert_isolation(monkeypatch):
    monkeypatch.setattr(charts, "get_entitlements", AsyncMock(return_value={"chartLimit": 4}))
    class Collection:
        async def update_one(self, filter, update, upsert):
            assert filter == {"user_id": "member-a", "slot": 2}
            assert update["$set"]["config"]["symbol"] == "ETH-USD"
            assert upsert
    class FakeDB: member_chart_settings=Collection()
    monkeypatch.setattr(charts, "db", FakeDB())
    result=run(charts.save_chart(2,charts.ChartConfig(symbol="eth-usd",seconds=300),user={"id":"member-a"}))
    assert result["order_submission_enabled"] is False
