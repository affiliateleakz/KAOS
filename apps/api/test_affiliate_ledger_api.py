import os
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "kaos_test")
import asyncio
from decimal import Decimal

import pytest
from fastapi import HTTPException

from db import db
import services_affiliate_ledger as ledger
from routes_affiliate import record_commission, reverse_commission, set_commission_status, CommActionReq
from routes_billing import DEFAULT_PLANS

loop = asyncio.new_event_loop()
run = loop.run_until_complete
# Preserve a historical paid amount to verify refunds/accounting across repricing.
YEARLY = {**next(p for p in DEFAULT_PLANS if p["id"] == "ultimate"), "amount": 14900}
COLLS = ["users", "affiliate_accounts", "commissions", "affiliate_customer_referrals", "settings",
         "affiliate_ledger_entries", "affiliate_ledger_payments", "affiliate_ledger_reversals"]


async def _seed():
    for c in COLLS:
        await db[c].delete_many({})
    await ledger.ensure_indexes()
    users = [("A", "ACTIVE", "ultimate", None), ("B", "ACTIVE", "monthly", "CODEA"),
             ("C", "EXPIRED", "pro", "CODEB"), ("D", "ACTIVE", "ultimate", "CODEC")]
    for uid, status, plan, ref in users:
        await db.users.insert_one({"id": uid, "membership_status": status, "membership_plan": plan,
                                   "referredByCode": ref})
        await db.affiliate_accounts.insert_one({"userId": uid, "code": f"CODE{uid}"})


@pytest.fixture(autouse=True)
def seed():
    run(_seed())


def amounts(entries):
    return {(e.affiliate_id, e.level, e.recipient_tier): e.amount for e in entries}


def test_three_levels_use_each_receivers_tier():
    entries = run(record_commission({"id": "D"}, YEARLY, "purchase", event_id="checkout:1"))
    assert amounts(entries) == {("C", 1, "free"): Decimal("14.90"), ("B", 2, "pro"): Decimal("22.35"),
                                ("A", 3, "ultimate"): Decimal("7.45")}
    assert run(db.commissions.count_documents({})) == 3


def test_duplicate_event_is_idempotent():
    run(record_commission({"id": "D"}, YEARLY, "purchase", event_id="checkout:1"))
    run(record_commission({"id": "D"}, YEARLY, "purchase", event_id="checkout:1"))
    assert run(db.affiliate_ledger_entries.count_documents({})) == 3
    assert run(db.commissions.count_documents({})) == 3


def test_partial_then_full_refund_and_over_refund():
    run(record_commission({"id": "D"}, YEARLY, "purchase", event_id="checkout:1"))
    part = run(reverse_commission("D", "refund", event_id="checkout:1", amount_cents=10000, reversal_id="r1"))
    assert sorted(e.amount for e in part) == [Decimal("-15.00"), Decimal("-10.00"), Decimal("-5.00")]
    run(reverse_commission("D", "refund", event_id="checkout:1"))
    for uid in "ABC":
        bal = run(ledger.statement(uid))["balance"]
        assert Decimal(bal["pending"]) + Decimal(bal["available"]) == 0
    with pytest.raises(ValueError):
        run(reverse_commission("D", "refund", event_id="checkout:1", amount_cents=1, reversal_id="r3"))


def test_renewal_and_referral_cycle_terminates():
    run(db.users.update_one({"id": "A"}, {"$set": {"referredByCode": "CODED"}}))
    entries = run(record_commission({"id": "D"}, YEARLY, "renewal", event_id="invoice:1", amount_cents=14900))
    assert {e.kind for e in entries} == {"renewal"} and len(entries) == 3


def test_statement_never_shows_payouts_and_paid_status_blocked():
    run(record_commission({"id": "D"}, YEARLY, "purchase", event_id="checkout:1"))
    st = run(ledger.statement("B"))
    assert st["payoutsEnabled"] is False and st["balance"]["paid"] == "0"
    assert Decimal(st["balance"]["pending"]) == Decimal("22.35")
    cid = run(db.commissions.find_one({"affiliateUserId": "B"}))["id"]
    with pytest.raises(HTTPException) as exc:
        run(set_commission_status(cid, CommActionReq(status="PAID"), admin={"id": "owner"}))
    assert exc.value.status_code == 403


def test_buyer_without_sponsor_creates_no_commission():
    assert run(record_commission({"id": "A"}, YEARLY, "purchase", event_id="checkout:2")) == []


def test_legacy_plan_ids_map_to_new_tiers():
    from routes_billing import find_plan
    assert find_plan(DEFAULT_PLANS, "monthly")["id"] == "pro"
    assert find_plan(DEFAULT_PLANS, "yearly")["id"] == "ultimate"
    assert [p["amount"] for p in DEFAULT_PLANS] == [2995, 9995, 29995, 99595]
    assert {p["interval"] for p in DEFAULT_PLANS} == {"month", "year"}


def test_annual_payments_use_full_paid_amount_and_annual_receiver_tiers():
    run(db.users.update_one({"id": "A"}, {"$set": {"membership_plan": "ultimate_yearly"}}))
    run(db.users.update_one({"id": "B"}, {"$set": {"membership_plan": "pro_yearly"}}))
    plan = next(p for p in DEFAULT_PLANS if p['id'] == 'ultimate_yearly')
    entries = run(record_commission({'id':'D'}, plan, 'purchase', event_id='annual:1'))
    assert amounts(entries) == {('C',1,'free'):Decimal('99.60'),('B',2,'pro'):Decimal('149.39'),('A',3,'ultimate'):Decimal('49.80')}
