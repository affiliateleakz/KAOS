import asyncio
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
import routes_free_apis as api

def run(c):return asyncio.run(c)

def test_paid_and_unverified_sources_excluded():
    ids={s["id"] for s in api.SOURCES}
    assert not {"finviz","messari","invo"} & ids
    assert all(s["access"] in ("free_public","free_key") for s in api.SOURCES)
    assert all(not s["key_required"] for s in api.SOURCES if s["access"]=="free_public")

def test_no_key_accepted_for_public_data_source():
    with pytest.raises(HTTPException) as e:
        run(api.save_key("coinbase_public",api.KeyInput(api_key="sample-secret-key"),admin={"id":"admin"}))
    assert e.value.status_code==422

def test_encrypted_at_rest_and_never_echoed(monkeypatch):
    class Cipher:
        def encrypt(self,data):
            assert data == b"fake-secret-1234"
            return b"encrypted-value"
    class Collection:
        async def update_one(self,filter,update,upsert):
            assert filter=={"provider":"fred_free"}
            assert update["$set"]["key_enc"]=="encrypted-value"
            assert "fake-secret" not in str(update)
    class FakeDB:
        admin_free_api_credentials=Collection()
    monkeypatch.setattr(api,"vault",lambda:Cipher())
    monkeypatch.setattr(api,"db",FakeDB())
    result=run(api.save_key("fred_free",api.KeyInput(api_key="fake-secret-1234"),admin={"id":"admin"}))
    assert result["key_saved"] is True
    assert result["connected"] is False
    assert "api_key" not in result and "key_enc" not in result
