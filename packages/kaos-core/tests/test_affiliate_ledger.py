from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from kaos.affiliate_ledger import CommissionLedger, PayoutsDisabled, has_permission
from kaos.memberships import Affiliate

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def members(**tiers):
    """Chain buyer -> l1 -> l2 -> l3 -> l4 with the given recipient tiers."""
    chain = ["buyer", "l1", "l2", "l3", "l4"]
    out = {}
    for i, mid in enumerate(chain):
        ref = chain[i + 1] if i + 1 < len(chain) else None
        out[mid] = Affiliate(mid, tiers.get(mid, "free"), ref)
    return out


def amounts(entries):
    return {(e.affiliate_id, e.level): e.amount for e in entries}


def test_all_ultimate_three_levels_only():
    led = CommissionLedger(members(l1="ultimate", l2="ultimate", l3="ultimate", l4="ultimate"))
    out = led.record_payment("pay1", "buyer", "pro", 49, at=T0)
    assert amounts(out) == {("l1", 1): Decimal("24.50"), ("l2", 2): Decimal("12.25"), ("l3", 3): Decimal("2.45")}


def test_rates_follow_recipient_tier_not_buyer_tier():
    led = CommissionLedger(members(buyer="free", l1="free", l2="pro", l3="pro"))
    out = led.record_payment("pay1", "buyer", "ultimate", 149, at=T0)
    # free L1 10%, pro L2 15%, pro L3 0% (no entry)
    assert amounts(out) == {("l1", 1): Decimal("14.90"), ("l2", 2): Decimal("22.35")}


def test_free_recipient_gets_nothing_beyond_level_one():
    led = CommissionLedger(members(l1="pro", l2="free", l3="ultimate"))
    out = led.record_payment("pay1", "buyer", "pro", 49, at=T0)
    assert amounts(out) == {("l1", 1): Decimal("14.70"), ("l3", 3): Decimal("2.45")}


def test_free_plan_and_zero_amount_create_no_commission():
    led = CommissionLedger(members(l1="ultimate"))
    assert led.record_payment("pay0", "buyer", "free", 0, at=T0) == []


def test_recruitment_or_unknown_kinds_do_not_qualify():
    led = CommissionLedger(members(l1="ultimate"))
    with pytest.raises(ValueError):
        led.record_payment("signup", "buyer", "pro", 49, kind="signup")


def test_idempotent_on_event_id():
    led = CommissionLedger(members(l1="pro"))
    first = led.record_payment("pay1", "buyer", "pro", 49, at=T0)
    again = led.record_payment("pay1", "buyer", "pro", 49, at=T0)
    assert first == again and len(led.entries) == 1


def test_recurring_renewals_each_earn_and_use_current_tier():
    m = members(l1="free")
    led = CommissionLedger(m)
    led.record_payment("m1", "buyer", "pro", 49, at=T0)
    m["l1"] = Affiliate("l1", "ultimate", "l2")  # recipient upgrades
    led.record_payment("m2", "buyer", "pro", 49, kind="renewal", at=T0 + timedelta(days=30))
    by_event = {e.event_id: e.amount for e in led.entries}
    assert by_event == {"m1": Decimal("4.90"), "m2": Decimal("24.50")}
    # earlier entry keeps the rate snapshotted at payment time
    assert led.entries[0].rate_pct == 10


def test_full_refund_reverses_all_levels():
    led = CommissionLedger(members(l1="ultimate", l2="ultimate", l3="ultimate"))
    led.record_payment("pay1", "buyer", "ultimate", 149, at=T0)
    led.record_reversal("ref1", "pay1", at=T0 + timedelta(days=3))
    for aff in ("l1", "l2", "l3"):
        assert led.balance(aff, as_of=T0 + timedelta(days=60))["available"] == 0


def test_partial_refund_and_chargeback_cannot_exceed_payment():
    led = CommissionLedger(members(l1="pro"))
    led.record_payment("pay1", "buyer", "pro", 49, at=T0)
    led.record_reversal("ref1", "pay1", amount=19, at=T0)
    assert led.balance("l1", as_of=T0)["reversed"] == Decimal("-5.70")
    with pytest.raises(ValueError):
        led.record_reversal("cb1", "pay1", amount=31, kind="chargeback", at=T0)
    led.record_reversal("cb1", "pay1", kind="chargeback", at=T0)  # remaining 30
    assert led.balance("l1", as_of=T0 + timedelta(days=31))["available"] == 0
    # reversal idempotency
    led.record_reversal("cb1", "pay1", kind="chargeback", at=T0)
    assert len([e for e in led.entries if e.event_id == "cb1"]) == 1


def test_hold_period_moves_pending_to_available():
    led = CommissionLedger(members(l1="pro"), hold_days=30)
    led.record_payment("pay1", "buyer", "pro", 49, at=T0)
    assert led.balance("l1", as_of=T0 + timedelta(days=1))["pending"] == Decimal("14.70")
    assert led.balance("l1", as_of=T0 + timedelta(days=30))["available"] == Decimal("14.70")


def test_referral_cycle_and_unknown_members_rejected():
    m = {"a": Affiliate("a", "pro", "b"), "b": Affiliate("b", "pro", "a")}
    with pytest.raises(ValueError):
        CommissionLedger(m).record_payment("p", "a", "pro", 49)
    with pytest.raises(KeyError):
        CommissionLedger({"a": Affiliate("a", "pro", "ghost")}).record_payment("p", "a", "pro", 49)
    with pytest.raises(KeyError):
        CommissionLedger({}).record_payment("p", "nobody", "pro", 49)


def test_payouts_are_disabled():
    led = CommissionLedger(members(l1="pro"))
    with pytest.raises(PayoutsDisabled):
        led.payout("l1")
    assert led.balance("l1")["paid"] == 0


def test_feature_gating():
    assert has_permission("free", "strategy") and not has_permission("free", "scanners")
    assert has_permission("pro", "ai_insights") and not has_permission("pro", "ai_execution")
    assert has_permission("ultimate", "ai_execution")
    assert not has_permission("unknown", "strategy")
