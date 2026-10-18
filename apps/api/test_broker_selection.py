import asyncio
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
import routes_broker_selection as selection

def run(coro):
    return asyncio.run(coro)

def test_rejects_unknown_broker():
    with pytest.raises(HTTPException) as err:
        run(selection.save_preference(selection.Preference(broker="fake-broker"), user={"id":"user-a"}))
    assert err.value.status_code == 422

def test_saved_selection_is_member_scoped_and_never_authorizes_orders(monkeypatch):
    saved = []
    class Collection:
        async def update_one(self, where, update, upsert):
            saved.append((where, update, upsert))
    class DB:
        member_broker_selections = Collection()
    monkeypatch.setattr(selection, "db", DB())
    result = run(selection.save_preference(selection.Preference(broker="coinbase"),user={"id":"user-a"}))
    assert saved == [({"user_id":"user-a"},{"$set":{"user_id":"user-a","broker":"coinbase"}},True)]
    assert result["live_order_authorized"] is False
