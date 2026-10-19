"""Guard against reversing partially written affiliate payments."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
import services_affiliate_ledger as ledger

def test_reversal_refuses_incomplete_underlying_payment(monkeypatch):
    db=SimpleNamespace(
        affiliate_ledger_reversals=SimpleNamespace(find_one=AsyncMock(return_value=None)),
        affiliate_ledger_payments=SimpleNamespace(find_one=AsyncMock(return_value={
            "event_id":"invoice:1", "state":"pending_entries"
        }))
    )
    monkeypatch.setattr(ledger,"db",db)
    with pytest.raises(RuntimeError,match="reconciled before reversal"):
        asyncio.run(ledger.record_reversal("rev:1","invoice:1"))
