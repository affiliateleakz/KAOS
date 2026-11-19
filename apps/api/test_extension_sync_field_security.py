"""Cloud strategy sync cannot set publication, verification or engagement fields."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
import routes_extension as ext
from models import SyncPushReq

@pytest.mark.parametrize("field,value", [
    ("published", True), ("verified", True), ("likesCount", 9000),
    ("moderationStatus", "approved"), ("featured", True),
])
def test_sync_rejects_server_managed_fields(monkeypatch, field, value):
    strategies = SimpleNamespace(find_one=AsyncMock(), insert_one=AsyncMock(),
                                 update_one=AsyncMock())
    monkeypatch.setattr(ext, "db", SimpleNamespace(strategies=strategies))
    request = SyncPushReq(strategies=[{"id": "strategy-1", "name": "Test", field: value}])
    with pytest.raises(HTTPException) as exc:
        asyncio.run(ext.sync_push(request, user={"id": "member-1"}))
    assert exc.value.status_code == 422
    strategies.find_one.assert_not_awaited()
    strategies.insert_one.assert_not_awaited()
    strategies.update_one.assert_not_awaited()
