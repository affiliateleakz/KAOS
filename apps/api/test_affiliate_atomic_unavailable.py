"""Fail-closed behavior when required MongoDB sessions cannot start."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
import affiliate_atomic as atomic

def test_required_transaction_unavailable_never_writes_payment(monkeypatch):
    monkeypatch.setenv("KAOS_AFFILIATE_TXN_MODE","required")
    db=SimpleNamespace(
        client=SimpleNamespace(start_session=AsyncMock(side_effect=RuntimeError("sessions unsupported"))),
        affiliate_ledger_payments=SimpleNamespace(insert_one=AsyncMock()),
        affiliate_ledger_entries=SimpleNamespace(insert_many=AsyncMock()))
    with pytest.raises(RuntimeError,match="sessions unsupported"):
        asyncio.run(atomic.write_payment({"event_id":"evt1"},[{"entry_id":"1"}],database=db))
    db.affiliate_ledger_payments.insert_one.assert_not_awaited()
    db.affiliate_ledger_entries.insert_many.assert_not_awaited()
