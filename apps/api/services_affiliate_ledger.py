"""Persist the receiver-based 3-level ledger (packages/kaos-core) in Mongo. Accounting preview only: no payouts."""
from datetime import datetime, timezone
from decimal import Decimal

from kaos.affiliate_ledger import CommissionLedger, Payment, Entry, MAX_LEVELS, PayoutsDisabled  # noqa: F401
from kaos.memberships import Affiliate, PRICES

from db import db

ACTIVE_STATES = ("ACTIVE", "TRIAL")


def plan_tier(plan):
    """Ledger tier for an API plan config. Plans without an explicit 'tier' count as 'pro'."""
    tier = (plan or {}).get("tier") or "pro"
    return tier if tier in PRICES else "pro"


async def member_tier(user):
    if not user or user.get("membership_status") not in ACTIVE_STATES:
        return "free"
    from routes_billing import get_plans
    plans = await get_plans()
    return plan_tier(next((p for p in plans if p["id"] == user.get("membership_plan")), None))


async def _referrer_id(user):
    code = user.get("referredByCode")
    if not code:
        return None
    acc = await db.affiliate_accounts.find_one({"code": code}, {"userId": 1})
    return acc["userId"] if acc else None


async def _members(buyer_id):
    """Buyer plus up to MAX_LEVELS sponsors with their current tiers. Cycles and missing users end the chain."""
    members, current, prev = {}, buyer_id, None
    while current and len(members) <= MAX_LEVELS:
        user = await db.users.find_one({"id": current}, {"_id": 0})
        if not user:
            members[prev] = Affiliate(prev, members[prev].tier, None)
            break
        ref = await _referrer_id(user)
        if ref == current or ref in members:
            ref = None
        tier = "free" if current == buyer_id else await member_tier(user)
        members[current] = Affiliate(current, tier, ref)
        prev, current = current, ref
    return members


def _entry_doc(e):
    return {"entry_id": e.entry_id, "event_id": e.event_id, "affiliate_id": e.affiliate_id, "buyer_id": e.buyer_id,
            "level": e.level, "recipient_tier": e.recipient_tier, "rate_pct": e.rate_pct,
            "base_amount": str(e.base_amount), "amount": str(e.amount), "kind": e.kind,
            "created_at": e.created_at.isoformat(), "available_at": e.available_at.isoformat()}


def _entry(d):
    return Entry(d["entry_id"], d["event_id"], d["affiliate_id"], d["buyer_id"], d["level"], d["recipient_tier"],
                 d["rate_pct"], Decimal(d["base_amount"]), Decimal(d["amount"]), d["kind"],
                 datetime.fromisoformat(d["created_at"]), datetime.fromisoformat(d["available_at"]))


async def ensure_indexes():
    await db.affiliate_ledger_entries.create_index("entry_id", unique=True)
    await db.affiliate_ledger_entries.create_index("affiliate_id")
    await db.affiliate_ledger_payments.create_index("event_id", unique=True)
    await db.affiliate_ledger_reversals.create_index("reversal_id", unique=True)


async def _entries_for(event_id):
    return [_entry(d) for d in await db.affiliate_ledger_entries.find({"event_id": event_id}, {"_id": 0}).to_list(10)]


async def record_payment(event_id, buyer_id, plan, amount_cents, kind="initial", at=None):
    """Record a settled initial/renewal payment. Idempotent on event_id."""
    if await db.affiliate_ledger_payments.find_one({"event_id": event_id}):
        return await _entries_for(event_id)
    ledger = CommissionLedger(await _members(buyer_id))
    at = at or datetime.now(timezone.utc)
    entries = ledger.record_payment(event_id, buyer_id, plan_tier(plan), Decimal(amount_cents) / 100, kind, at)
    p = ledger.payments[event_id]
    await db.affiliate_ledger_payments.insert_one({
        "event_id": event_id, "buyer_id": buyer_id, "plan": p.plan, "plan_id": (plan or {}).get("id"),
        "amount": str(p.amount), "kind": kind, "at": at.isoformat(), "reversed_amount": "0"})
    if entries:
        await db.affiliate_ledger_entries.insert_many([_entry_doc(e) for e in entries])
    return entries


async def record_reversal(reversal_id, event_id, amount_cents=None, kind="refund", at=None):
    """Offset a payment's commissions (full when amount_cents is None). Idempotent on reversal_id."""
    if await db.affiliate_ledger_reversals.find_one({"reversal_id": reversal_id}):
        return await _entries_for(reversal_id)
    pd = await db.affiliate_ledger_payments.find_one({"event_id": event_id})
    if not pd:
        raise KeyError(event_id)
    ledger = CommissionLedger({})
    ledger.payments[event_id] = Payment(event_id, pd["buyer_id"], pd["plan"], Decimal(pd["amount"]), pd["kind"],
                                        datetime.fromisoformat(pd["at"]), Decimal(pd["reversed_amount"]))
    ledger.entries = await _entries_for(event_id)
    amount = None if amount_cents is None else Decimal(amount_cents) / 100
    entries = ledger.record_reversal(reversal_id, event_id, amount, kind, at)
    await db.affiliate_ledger_reversals.insert_one({"reversal_id": reversal_id, "event_id": event_id, "kind": kind})
    await db.affiliate_ledger_payments.update_one(
        {"event_id": event_id}, {"$set": {"reversed_amount": str(ledger.payments[event_id].reversed_amount)}})
    if entries:
        await db.affiliate_ledger_entries.insert_many([_entry_doc(e) for e in entries])
    return entries


async def reverse_all_for_buyer(buyer_id, kind="refund", prefix="rev"):
    """Fully reverse every not-yet-reversed payment by a buyer."""
    out = []
    async for pd in db.affiliate_ledger_payments.find({"buyer_id": buyer_id}):
        if Decimal(pd["reversed_amount"]) < Decimal(pd["amount"]):
            out += await record_reversal(f"{prefix}:{pd['event_id']}", pd["event_id"], None, kind)
    return out


async def statement(affiliate_id, as_of=None):
    docs = await db.affiliate_ledger_entries.find({"affiliate_id": affiliate_id}, {"_id": 0}) \
        .sort("created_at", -1).to_list(1000)
    ledger = CommissionLedger({}, entries=[_entry(d) for d in docs])
    bal = {k: str(v) for k, v in ledger.balance(affiliate_id, as_of).items()}
    return {"balance": bal, "entries": docs, "payoutsEnabled": False,
            "note": "Preview only. Payouts are disabled pending compliance, KYC/tax and founder approval."}
