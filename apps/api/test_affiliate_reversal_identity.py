"""Prevent replaying a reversal ID for a different payment or reversal type."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
import services_affiliate_ledger as ledger

@pytest.mark.parametrize("requested_event,requested_kind", [
    ("payment_other","refund"),("payment_original","chargeback")
])
def test_reversal_id_cannot_change_financial_identity(monkeypatch,requested_event,requested_kind):
    existing={"reversal_id":"refund_1","event_id":"payment_original",
              "kind":"refund","state":"completed"}
    reversals=SimpleNamespace(find_one=AsyncMock(return_value=existing))
    monkeypatch.setattr(ledger,"db",SimpleNamespace(affiliate_ledger_reversals=reversals))
    with pytest.raises(RuntimeError,match="mismatched financial details"):
        asyncio.run(ledger.record_reversal("refund_1",requested_event,kind=requested_kind))
