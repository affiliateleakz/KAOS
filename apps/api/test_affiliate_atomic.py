"""Transaction mode must use one MongoDB session across all journal writes."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
import pytest
import affiliate_atomic as atomic

class Txn:
    entered=0
    async def __aenter__(self):
        self.entered += 1
        return self
    async def __aexit__(self, *args):
        return False

class Session:
    def __init__(self):
        self.txn=Txn()
    async def __aenter__(self):
        return self
    async def __aexit__(self,*args):
        return False
    def start_transaction(self):
        return self.txn

def db_fixture():
    session=Session()
    return SimpleNamespace(
        client=SimpleNamespace(start_session=AsyncMock(return_value=session)),
        affiliate_ledger_payments=SimpleNamespace(insert_one=AsyncMock(),
            update_one=AsyncMock(return_value=SimpleNamespace(modified_count=1))),
        affiliate_ledger_reversals=SimpleNamespace(insert_one=AsyncMock()),
        affiliate_ledger_entries=SimpleNamespace(insert_many=AsyncMock())
    ),session

def test_required_payment_uses_one_transaction(monkeypatch):
    monkeypatch.setenv("KAOS_AFFILIATE_TXN_MODE","required")
    db,session=db_fixture()
    asyncio.run(atomic.write_payment({"event_id":"evt1"},[{"entry_id":"a"}],database=db))
    assert session.txn.entered==1
    assert db.affiliate_ledger_payments.insert_one.await_args.kwargs["session"] is session
    assert db.affiliate_ledger_entries.insert_many.await_args.kwargs["session"] is session
    db.affiliate_ledger_payments.update_one.assert_not_awaited()

def test_required_reversal_failure_aborts_instead_of_acknowledging(monkeypatch):
    monkeypatch.setenv("KAOS_AFFILIATE_TXN_MODE","required")
    db,session=db_fixture()
    db.affiliate_ledger_payments.update_one.return_value=SimpleNamespace(modified_count=0)
    with pytest.raises(RuntimeError,match="transaction aborted"):
        asyncio.run(atomic.write_reversal({"reversal_id":"rev1"},"evt1","0","10",[],database=db))
    assert session.txn.entered==1
    assert db.affiliate_ledger_reversals.insert_one.await_args.kwargs["session"] is session
    db.affiliate_ledger_entries.insert_many.assert_not_awaited()
