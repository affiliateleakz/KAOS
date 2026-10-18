import asyncio
from unittest.mock import AsyncMock
import pytest
import sec_13f_collector as collector
import routes_disclosures as api
from fastapi import HTTPException

def test_invalid_cik():
    with pytest.raises(ValueError):
        asyncio.run(collector.fetch_13f_holdings(-1))

def test_user_agent_required(monkeypatch):
    monkeypatch.delenv("KAOS_SEC_USER_AGENT",raising=False)
    with pytest.raises(RuntimeError,match="User-Agent"):
        asyncio.run(collector.fetch_13f_holdings(123456,client=object()))

def test_refresh_requires_collector_key(monkeypatch):
    monkeypatch.setenv("KAOS_COLLECTOR_KEY","secret")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(api.refresh_sec_13f(123456,x_kaos_collector_key="wrong"))
    assert exc.value.status_code==403
