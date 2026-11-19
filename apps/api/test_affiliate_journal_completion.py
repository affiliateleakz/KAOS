"""Ledger must not acknowledge financial events unless completion write succeeds."""
import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
import services_affiliate_ledger as ledger
from kaos.memberships import Affiliate

def test_payment_completion_write_must_succeed(monkeypatch):
    buyer="buyer"; sponsor="sponsor"
    monkeypatch.setattr(ledger,"_members",AsyncMock(return_value={
        buyer: Affiliate(buyer,"free",sponsor),
        sponsor: Affiliate(sponsor,"pro",None)
    }))
    payments=SimpleNamespace(find_one=AsyncMock(return_value=None),insert_one=AsyncMock(),
                              update_one=AsyncMock(return_value=SimpleNamespace(modified_count=0)))
    entries=SimpleNamespace(insert_many=AsyncMock())
    monkeypatch.setattr(ledger,"db",SimpleNamespace(affiliate_ledger_payments=payments,
                                                    affiliate_ledger_entries=entries))
    with pytest.raises(RuntimeError,match="completion could not be confirmed"):
        asyncio.run(ledger.record_payment("checkout:e1",buyer,{"tier":"pro","id":"pro"},4900))

def test_reversal_completion_write_must_succeed(monkeypatch):
    payment={"event_id":"checkout:e1","buyer_id":"buyer","plan":"pro","amount":"49",
             "kind":"initial","at":datetime.now(timezone.utc).isoformat(),
             "reversed_amount":"0","state":"completed"}
    reversals=SimpleNamespace(find_one=AsyncMock(return_value=None),insert_one=AsyncMock(),
                             update_one=AsyncMock(return_value=SimpleNamespace(modified_count=0)))
    payments=SimpleNamespace(find_one=AsyncMock(return_value=payment),
                             update_one=AsyncMock(return_value=SimpleNamespace(modified_count=1)))
    monkeypatch.setattr(ledger,"db",SimpleNamespace(affiliate_ledger_payments=payments,
                                                    affiliate_ledger_reversals=reversals))
    monkeypatch.setattr(ledger,"_entries_for",AsyncMock(return_value=[]))
    with pytest.raises(RuntimeError,match="completion could not be confirmed"):
        asyncio.run(ledger.record_reversal("rev:e1","checkout:e1",amount_cents=100))
