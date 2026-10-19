from datetime import datetime,timezone
import pytest
from fastapi import HTTPException
from routes_owner_candles import require_owner
from candle_research_worker import normalize

def test_only_named_owner(monkeypatch):
    monkeypatch.setenv("KAOS_CANDLE_OWNER_USER_ID","correct-id")
    with pytest.raises(HTTPException):
        require_owner({"id":"another-admin","role":"super_admin"})
    with pytest.raises(HTTPException):
        require_owner({"id":"correct-id","role":"user"})
    assert require_owner({"id":"correct-id","role":"super_admin"})["id"]=="correct-id"

def test_fail_closed_without_owner(monkeypatch):
    monkeypatch.delenv("KAOS_CANDLE_OWNER_USER_ID",raising=False)
    with pytest.raises(HTTPException):
        require_owner({"id":"correct-id","role":"super_admin"})

def test_closed_only_and_valid_ohlcv():
    now=datetime.fromtimestamp(1800000300,tz=timezone.utc)
    raw=[[1800000000,99,103,100,102,100],
         [1800000300,100,103,101,102,80],
         [1799999940,100,99,100,101,50]]
    result=normalize(raw,"BTC-USD",300,now)
    assert len(result)==1
    assert result[0]["ts"]==1800000000*1000
    assert result[0]["source"]=="coinbase_exchange_public_candles"
