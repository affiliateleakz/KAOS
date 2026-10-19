import asyncio
import pytest
from fastapi import HTTPException
import routes_research_replay as api

def candle(ts):
    return api.Candle(ts=ts,open=100,high=101,low=99,close=100)

def test_structure_replay_no_fake_trades():
    req=api.StructureReplayRequest(candles=[candle(i*15000) for i in range(50)])
    result=asyncio.run(api.structure_replay_endpoint(req,user={"id":"member"}))
    assert result["research_only"] is True
    assert result["execution_enabled"] is False
    assert result["summary"]["trades"]==0

def test_structure_replay_rejects_missing_bar():
    rows=[candle(i*15000) for i in range(40)]
    rows[20].ts+=1
    req=api.StructureReplayRequest(candles=rows)
    with pytest.raises(HTTPException) as err:
        asyncio.run(api.structure_replay_endpoint(req,user={"id":"member"}))
    assert err.value.status_code==422
