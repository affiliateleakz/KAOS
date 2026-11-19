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

def test_checkout_commission_errors_propagate(monkeypatch):
    from datetime import datetime, timezone
    user={"id":"buyer1","email":"buyer@example.test"}
    plan={"id":"pro","interval":"month"}
    db=SimpleNamespace(
        subscriptions=SimpleNamespace(update_one=AsyncMock(),find_one=AsyncMock(return_value={"session_id":"session1"})),
        affiliate_ledger_payments=SimpleNamespace(find_one=AsyncMock(return_value=None)),
        users=SimpleNamespace(update_one=AsyncMock(),find_one=AsyncMock(return_value=user)))
    monkeypatch.setattr(billing,"db",db)
    monkeypatch.setattr(billing,"get_plans",AsyncMock(return_value=[plan]))
    monkeypatch.setattr(billing,"_verified_subscription",AsyncMock(return_value={"status":"active","current_period_end":4102444800}))
    monkeypatch.setattr(billing,"_checkout_invoice",AsyncMock(return_value={"id":"in1","amount_paid":2995}))
    import routes_affiliate
    async def fail(*args,**kwargs):
        raise RuntimeError("commission storage offline")
    monkeypatch.setattr(routes_affiliate,"record_commission",fail)
    with pytest.raises(RuntimeError,match="commission storage offline"):
        asyncio.run(billing._activate("buyer1","pro","cus1","sub1","session1"))

def test_refund_does_not_guess_latest_buyer_payment(monkeypatch):
    payments=SimpleNamespace(find_one=AsyncMock(return_value=None))
    db=SimpleNamespace(users=SimpleNamespace(find_one=AsyncMock(return_value={"id":"buyer1"})),
                       affiliate_ledger_payments=payments)
    monkeypatch.setattr(billing,"db",db)
    with pytest.raises(RuntimeError,match="payment journal not found"):
        asyncio.run(billing._reverse_for_charge(
            {"id":"ch1","invoice":"inv_unknown","customer":"cus1","amount_refunded":500}, "refund"))
    assert payments.find_one.await_args_list[0].args[0]=={"event_id":"invoice:inv_unknown"}
    assert payments.find_one.await_args_list[1].args[0]=={"invoice_id":"inv_unknown","buyer_id":"buyer1"}

def test_refund_rejects_cross_customer_payment(monkeypatch):
    payments=SimpleNamespace(find_one=AsyncMock(return_value={
        "event_id":"invoice:inv1","buyer_id":"someone_else","amount":"10","reversed_amount":"0"}))
    db=SimpleNamespace(users=SimpleNamespace(find_one=AsyncMock(return_value={"id":"buyer1"})),
                       affiliate_ledger_payments=payments)
    monkeypatch.setattr(billing,"db",db)
    with pytest.raises(RuntimeError,match="does not match"):
        asyncio.run(billing._reverse_for_charge(
            {"id":"ch1","invoice":"inv1","customer":"cus1","amount_refunded":500}, "refund"))

@pytest.mark.parametrize("reason,payload", [
    ("refund", {"invoice":"inv1","customer":"cus1","amount_refunded":500}),
    ("chargeback", {"id":"dp1","invoice":"inv1","customer":"cus1","amount":500}),
])
def test_reversal_requires_stable_charge_identifier(monkeypatch,reason,payload):
    db=SimpleNamespace(users=SimpleNamespace(find_one=AsyncMock()),
                       affiliate_ledger_payments=SimpleNamespace(find_one=AsyncMock()))
    monkeypatch.setattr(billing,"db",db)
    with pytest.raises(RuntimeError,match="missing charge identity"):
        asyncio.run(billing._reverse_for_charge(payload,reason))
    db.affiliate_ledger_payments.find_one.assert_not_awaited()

@pytest.mark.parametrize("customer", [None, "", "   "])
def test_refund_rejects_missing_customer_identity(monkeypatch, customer):
    users=SimpleNamespace(find_one=AsyncMock())
    payments=SimpleNamespace(find_one=AsyncMock())
    monkeypatch.setattr(billing,"db",SimpleNamespace(users=users,affiliate_ledger_payments=payments))
    with pytest.raises(RuntimeError, match="missing customer identity"):
        asyncio.run(billing._reverse_for_charge(
            {"id":"ch1","invoice":"inv1","customer":customer,"amount_refunded":500}, "refund"))
    users.find_one.assert_not_awaited()
    payments.find_one.assert_not_awaited()

def test_refund_rejects_unknown_customer_identity(monkeypatch):
    users=SimpleNamespace(find_one=AsyncMock(return_value=None))
    payments=SimpleNamespace(find_one=AsyncMock())
    monkeypatch.setattr(billing,"db",SimpleNamespace(users=users,affiliate_ledger_payments=payments))
    with pytest.raises(RuntimeError, match="customer not found"):
        asyncio.run(billing._reverse_for_charge(
            {"id":"ch1","invoice":"inv1","customer":"cus_unrecognized","amount_refunded":500}, "refund"))
    payments.find_one.assert_not_awaited()
