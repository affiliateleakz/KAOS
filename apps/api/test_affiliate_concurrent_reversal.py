"""A refund cannot overwrite a concurrent change to reversed totals."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
from decimal import Decimal
import pytest
import services_affiliate_ledger as ledger

def test_reversal_cas_detects_concurrent_modification(monkeypatch):
    payment={"event_id":"payment1","buyer_id":"buyer1","plan":"pro","amount":"49.00",
             "kind":"initial","at":"2026-10-19T00:00:00+00:00",
             "reversed_amount":"0","state":"completed"}
    payments=SimpleNamespace(find_one=AsyncMock(return_value=payment),
                             update_one=AsyncMock(return_value=SimpleNamespace(modified_count=0)))
    reversals=SimpleNamespace(find_one=AsyncMock(return_value=None),
                              insert_one=AsyncMock())
    monkeypatch.setattr(ledger,"db",SimpleNamespace(affiliate_ledger_payments=payments,
                  affiliate_ledger_reversals=reversals))
    monkeypatch.setattr(ledger,"_entries_for",AsyncMock(return_value=[]))
    with pytest.raises(RuntimeError,match="Concurrent affiliate reversal"):
        asyncio.run(ledger.record_reversal("reversal1","payment1",amount_cents=100))
    assert payments.update_one.await_args.args[0]["reversed_amount"]=="0"
