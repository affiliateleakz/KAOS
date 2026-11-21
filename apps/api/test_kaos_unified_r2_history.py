"""R2 history in KAOS Trading is owner-only, closed-candle and never a quote."""
import asyncio
import pytest
from fastapi import HTTPException
import routes_owner_candles as routes

def test_owner_only_archive_endpoint(monkeypatch):
    monkeypatch.setenv("KAOS_CANDLE_OWNER_USER_ID","owner-account")
    with pytest.raises(HTTPException) as err:
        routes.require_owner({"id":"other-account","role":"admin"})
    assert err.value.status_code==403

def test_r2_history_returns_source_identical_bars_without_order_authority(monkeypatch):
    market=routes.MARKETS[0]
    symbol,asset_class=market
    async def fake_archive(s,a,limit):
        assert (s,a,limit)==(symbol,asset_class,200)
        return [
            {"ts":1800000000000,"symbol":s,"asset_class":a,"seconds":60,
             "source":"strict-provider","open":1.0,"high":2.0,"low":.5,
             "close":1.2,"volume":50},
            {"ts":1800000060000,"symbol":s,"asset_class":a,"seconds":60,
             "source":"strict-provider","open":1.2,"high":2.1,"low":1.0,
             "close":1.3,"volume":30}
        ],"strict-provider"
    monkeypatch.setattr(routes,"_r2_market",fake_archive)
    result=asyncio.run(routes.r2_lab_history(symbol=symbol,limit=200,user={"id":"owner-account"}))
    assert result["source"]=="strict-provider"
    assert result["count"]==2
    assert result["last_closed_ts"]==1800000060000
    assert result["seconds"]==60
    assert result["research_only"] is True
    assert result["live_quote"] is False
    assert result["order_authorized"] is False
    assert set(result["candles"][0])=={"ts","open","high","low","close","volume"}

def test_unknown_market_never_read_from_archive(monkeypatch):
    async def forbidden(*args):
        raise AssertionError("Unknown markets must not call R2")
    monkeypatch.setattr(routes,"_r2_market",forbidden)
    with pytest.raises(HTTPException) as err:
        asyncio.run(routes.r2_lab_history(symbol="NOT-IN-R2",limit=200,user={"id":"owner"}))
    assert err.value.status_code==422
