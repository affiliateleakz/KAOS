"""Replayed refund IDs must not silently change their amounts."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
import services_affiliate_ledger as ledger

@pytest.mark.parametrize("old_amount,new_amount",[(1000,2000),(None,1000),(1000,None)])
def test_reversal_id_amount_replay_mismatch(monkeypatch,old_amount,new_amount):
    old={"reversal_id":"refund1","event_id":"payment1","kind":"refund",
         "state":"completed","requested_amount_cents":old_amount}
    mockdb=SimpleNamespace(affiliate_ledger_reversals=SimpleNamespace(find_one=AsyncMock(return_value=old)))
    monkeypatch.setattr(ledger,"db",mockdb)
    with pytest.raises(RuntimeError,match="mismatched financial details"):
        asyncio.run(ledger.record_reversal("refund1","payment1",amount_cents=new_amount))
