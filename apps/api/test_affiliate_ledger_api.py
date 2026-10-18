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
YEARLY = next(p for p in DEFAULT_PLANS if p["id"] == "yearly")
COLLS = ["users", "affiliate_accounts", "commissions", "affiliate_customer_referrals", "settings",
         "affiliate_ledger_entries", "affiliate_ledger_payments", "affiliate_ledger_reversals"]


async def _seed():
    for c in COLLS:
        await db[c].delete_many({})
    await ledger.ensure_indexes()
    users = [("A", "ACTIVE", "yearly", None), ("B", "ACTIVE", "monthly", "CODEA"),
             ("C", "EXPIRED", "monthly", "CODEB"), ("D", "ACTIVE", "yearly", "CODEC")]
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
    assert amounts(entries) == {("C", 1, "free"): Decimal("27.90"), ("B", 2, "pro"): Decimal("41.85"),
                                ("A", 3, "ultimate"): Decimal("13.95")}
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
    entries = run(record_commission({"id": "D"}, YEARLY, "renewal", event_id="invoice:1", amount_cents=27900))
    assert {e.kind for e in entries} == {"renewal"} and len(entries) == 3


def test_statement_never_shows_payouts_and_paid_status_blocked():
    run(record_commission({"id": "D"}, YEARLY, "purchase", event_id="checkout:1"))
    st = run(ledger.statement("B"))
    assert st["payoutsEnabled"] is False and st["balance"]["paid"] == "0"
    assert Decimal(st["balance"]["pending"]) == Decimal("41.85")
    cid = run(db.commissions.find_one({"affiliateUserId": "B"}))["id"]
    with pytest.raises(HTTPException) as exc:
        run(set_commission_status(cid, CommActionReq(status="PAID"), admin={"id": "owner"}))
    assert exc.value.status_code == 403


def test_buyer_without_sponsor_creates_no_commission():
    assert run(record_commission({"id": "A"}, YEARLY, "purchase", event_id="checkout:2")) == []
