"""Older payment records without a settled journal state cannot be reversed blindly."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
import services_affiliate_ledger as ledger

def test_legacy_payment_reversal_requires_review(monkeypatch):
    payments=SimpleNamespace(find_one=AsyncMock(return_value={"event_id":"legacy1","reversed_amount":"0"}))
    reversals=SimpleNamespace(find_one=AsyncMock(return_value=None))
    monkeypatch.setattr(ledger,"db",SimpleNamespace(affiliate_ledger_payments=payments,affiliate_ledger_reversals=reversals))
    with pytest.raises(RuntimeError,match="Legacy affiliate payment requires reconciliation"):
        asyncio.run(ledger.record_reversal("r-new","legacy1"))
