"""Reject a repeated Stripe event ID carrying different payment details."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
import services_affiliate_ledger as ledger

@pytest.mark.parametrize("existing", [
    {"event_id":"e1","state":"completed","buyer_id":"other","kind":"initial","amount":"49"},
    {"event_id":"e1","state":"completed","buyer_id":"buyer","kind":"renewal","amount":"49"},
    {"event_id":"e1","state":"completed","buyer_id":"buyer","kind":"initial","amount":"149"},
])
def test_completed_payment_id_mismatched_details_refused(monkeypatch,existing):
    monkeypatch.setattr(ledger,"db",SimpleNamespace(
        affiliate_ledger_payments=SimpleNamespace(find_one=AsyncMock(return_value=existing))))
    with pytest.raises(RuntimeError,match="mismatched financial details"):
        asyncio.run(ledger.record_payment("e1","buyer",{"id":"pro","tier":"pro"},4900))
