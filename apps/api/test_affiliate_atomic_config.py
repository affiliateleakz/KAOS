"""Invalid financial transaction configuration must fail before MongoDB writes."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
import affiliate_atomic as atomic

def test_invalid_transaction_mode_rejects_payment_without_writes(monkeypatch):
    monkeypatch.setenv("KAOS_AFFILIATE_TXN_MODE","requird")
    database=SimpleNamespace(affiliate_ledger_payments=SimpleNamespace(insert_one=AsyncMock()),
                             affiliate_ledger_entries=SimpleNamespace(insert_many=AsyncMock()))
    with pytest.raises(RuntimeError,match="Invalid KAOS_AFFILIATE_TXN_MODE"):
        asyncio.run(atomic.write_payment({"event_id":"event1"},[],database=database))
    database.affiliate_ledger_payments.insert_one.assert_not_awaited()
