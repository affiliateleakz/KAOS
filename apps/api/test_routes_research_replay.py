import asyncio
import pytest
from fastapi import HTTPException
from pydantic import ValidationError
import routes_research_replay as api

def candle(ts, value=100):
    return dict(ts=ts,open=value,high=value+.1,low=value-.1,close=value)

def test_replay_api_empty_signals_are_not_fake_results():
    req=api.ReplayRequest(minute_candles=[candle(i*60000) for i in range(65)],
                          fifteen_second_candles=[candle(i*15000) for i in range(260)])
    result=asyncio.run(api.trend_pause_replay(req,user={"id":"member-a"}))
    assert result["research_only"] and result["execution_enabled"] is False
    assert result["summary"]["trades"] == 0
    assert result["summary"]["win_rate_ex_ties"] is None

def test_request_bounded_and_invalid_input():
    with pytest.raises(ValidationError):
        api.ReplayRequest(minute_candles=[],fifteen_second_candles=[])
    with pytest.raises(ValidationError):
        api.ReplayRequest(minute_candles=[candle(i*60000) for i in range(53)],
                          fifteen_second_candles=[candle(i*15000) for i in range(24)],
                          horizon_seconds=13)

def test_bad_candle_order_rejected():
    req=api.ReplayRequest(minute_candles=[candle(i*60000) for i in range(53)],
                          fifteen_second_candles=[candle(0) for i in range(24)])
    with pytest.raises(HTTPException) as err:
        asyncio.run(api.trend_pause_replay(req,user={"id":"member-a"}))
    assert err.value.status_code == 422
