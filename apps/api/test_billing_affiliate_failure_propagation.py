"""Affiliate financial errors must keep Stripe webhook events retryable."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
import routes_billing as billing

def test_refund_reversal_errors_propagate(monkeypatch):
    user={"id":"buyer1"}
    payment={"event_id":"invoice:inv1","buyer_id":"buyer1","amount":"10","reversed_amount":"0"}
    db=SimpleNamespace(users=SimpleNamespace(find_one=AsyncMock(return_value=user)),
        affiliate_ledger_payments=SimpleNamespace(find_one=AsyncMock(return_value=payment)))
    monkeypatch.setattr(billing,"db",db)
    import routes_affiliate
    async def fail(*args,**kwargs):
        raise RuntimeError("ledger unavailable")
    monkeypatch.setattr(routes_affiliate,"reverse_commission",fail)
    with pytest.raises(RuntimeError,match="ledger unavailable"):
        asyncio.run(billing._reverse_for_charge(
            {"id":"ch1","invoice":"inv1","customer":"cus1","amount_refunded":1000}, "refund"))
