"""Unavailable KAOS AI must never output pseudo-random actionable directions."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import services_trading as st


def test_unconfigured_ai_has_no_buy_or_sell(monkeypatch):
    async def config():
        return {"aiModelVersion": "unconfigured"}
    monkeypatch.setattr(st, "get_trading_config", config)
    monkeypatch.setattr(st, "db", SimpleNamespace(
        ai_models=SimpleNamespace(find_one=AsyncMock(return_value=None))))
    result = asyncio.run(st.kaos_ai_predict(
        "SPY", "alpaca", {"bucket":"test", "featureVector": [1.0, 2.0]}))
    assert result["direction"] is None
    assert result["confidence"] is None
    assert result["simulated"] is True
    assert result["live"] is False
