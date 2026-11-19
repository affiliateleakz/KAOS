"""Incomplete reversal records are never silently accepted."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
import services_affiliate_ledger as ledger

def test_incomplete_reversal_requires_reconciliation(monkeypatch):
    reversals=SimpleNamespace(find_one=AsyncMock(return_value={"reversal_id":"r1","state":"pending_entries"}))
    monkeypatch.setattr(ledger,"db",SimpleNamespace(affiliate_ledger_reversals=reversals))
    with pytest.raises(RuntimeError,match="reversal requires ledger reconciliation"):
        asyncio.run(ledger.record_reversal("r1","invoice:1"))
