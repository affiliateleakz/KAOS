import asyncio
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
import routes_broker_selection as selection

def run(c):return asyncio.run(c)

def test_unknown_broker_cannot_be_selected():
    with pytest.raises(HTTPException) as e:
        run(selection.set_selection(selection.Selection(broker="made-up"),user={"id":"u"}))
    assert e.value.status_code==422

def test_member_specific_broker_preference_without_live_authorization(monkeypatch):
    class Collection:
        async def update_one(self,query,update,upsert=False):
            assert query=={"user_id":"member-A"}
            assert update["$set"]=={"user_id":"member-A","broker":"coinbase"}
            assert upsert is True
    class FakeDB: member_broker_selections=Collection()
    monkeypatch.setattr(selection,"db",FakeDB())
    result=run(selection.set_selection(selection.Selection(broker="coinbase"),user={"id":"member-A"}))
    assert result["broker"]=="coinbase"
    assert result["live_order_authorized"] is False
