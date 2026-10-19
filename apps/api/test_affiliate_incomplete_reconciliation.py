"""An incomplete affiliate payment cannot be treated as fully recorded."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
import services_affiliate_ledger as ledger

def test_pending_payment_requires_reconciliation(monkeypatch):
    payments=SimpleNamespace(find_one=AsyncMock(return_value={"event_id":"invoice:test","state":"pending_entries"}))
    monkeypatch.setattr(ledger,"db",SimpleNamespace(affiliate_ledger_payments=payments))
    with pytest.raises(RuntimeError,match="requires ledger reconciliation"):
        asyncio.run(ledger.record_payment("invoice:test","buyer1",{"tier":"pro"},4900))
