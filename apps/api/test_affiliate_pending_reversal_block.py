"""Do not stack additional refunds on a payment with an incomplete reversal."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
import services_affiliate_ledger as ledger

def test_new_reversal_blocked_by_prior_pending_reversal(monkeypatch):
    payments=SimpleNamespace(find_one=AsyncMock(return_value={
        "event_id":"invoice1","state":"completed"}))
    reversals=SimpleNamespace(find_one=AsyncMock(side_effect=[
        None, {"event_id":"invoice1","reversal_id":"old","state":"pending_entries"}]))
    monkeypatch.setattr(ledger,"db",SimpleNamespace(
        affiliate_ledger_payments=payments,affiliate_ledger_reversals=reversals))
    with pytest.raises(RuntimeError,match="Prior affiliate reversal"):
        asyncio.run(ledger.record_reversal("new","invoice1"))
    assert reversals.find_one.await_count==2
