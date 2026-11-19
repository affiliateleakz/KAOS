"""Manual paper orders do not impersonate server-verified market fills."""
import asyncio
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
import routes_paper as paper

def test_verified_quote_mode_rejects_client_supplied_fills(monkeypatch):
    monkeypatch.setenv("KAOS_PAPER_REQUIRE_VERIFIED_QUOTES","true")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(paper._submit({"id":"user1"},"BTC-USD","CRYPTO_SPOT","BUY","10","50000","test-id"))
    assert exc.value.status_code==503
    assert "not configured" in exc.value.detail
