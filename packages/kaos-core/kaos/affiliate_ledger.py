"""Receiver-based, three-level commission ledger (preview/accounting only).

Rates come from each *recipient's* tier at the time of the qualifying payment
(``memberships.RATES``). Only paid subscription payments (initial or renewal)
create commissions; recruitment itself never does. Refunds and chargebacks
create offsetting reversal entries. Payouts are intentionally disabled.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

from .memberships import RATES, PRICES, PERMISSIONS

CENT = Decimal("0.01")
QUALIFYING_KINDS = {"initial", "renewal"}
REVERSAL_KINDS = {"refund", "chargeback"}
DEFAULT_HOLD_DAYS = 30
MAX_LEVELS = 3


class PayoutsDisabled(RuntimeError):
    """Raised for any payout attempt; requires compliance/KYC/tax approval first."""


def has_permission(tier, feature):
    return feature in PERMISSIONS.get(tier, set())


def _money(value):
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Entry:
    entry_id: str
    event_id: str
    affiliate_id: str
    buyer_id: str
    level: int
    recipient_tier: str
    rate_pct: int
    base_amount: Decimal
    amount: Decimal
    kind: str
    created_at: datetime
    available_at: datetime


@dataclass
class Payment:
    event_id: str
    buyer_id: str
    plan: str
    amount: Decimal
    kind: str
    at: datetime
    reversed_amount: Decimal = Decimal("0")


@dataclass
class CommissionLedger:
    members: dict
    hold_days: int = DEFAULT_HOLD_DAYS
    entries: list = field(default_factory=list)
    payments: dict = field(default_factory=dict)
    reversals: set = field(default_factory=set)

    def upline(self, buyer_id):
        if buyer_id not in self.members:
            raise KeyError(buyer_id)
        chain, seen, current = [], {buyer_id}, self.members[buyer_id].referrer
        while current and len(chain) < MAX_LEVELS:
            if current in seen:
                raise ValueError("referral cycle")
            if current not in self.members:
                raise KeyError(current)
            seen.add(current)
            chain.append(self.members[current])
            current = self.members[current].referrer
        return chain

    def record_payment(self, event_id, buyer_id, plan, amount, kind="initial", at=None):
        """Record a settled subscription payment. Idempotent on ``event_id``."""
        if event_id in self.payments:
            return [e for e in self.entries if e.event_id == event_id]
        if kind not in QUALIFYING_KINDS:
            raise ValueError(f"non-qualifying payment kind: {kind}")
        if plan not in PRICES:
            raise ValueError(f"unknown plan: {plan}")
        base = _money(amount)
        if base < 0:
            raise ValueError("negative payment")
        at = at or datetime.now(timezone.utc)
        self.payments[event_id] = Payment(event_id, buyer_id, plan, base, kind, at)
        if base == 0:
            return []
        created = []
        for level, aff in enumerate(self.upline(buyer_id), start=1):
            rate = RATES[aff.tier][level - 1]
            if not rate:
                continue
            entry = Entry(
                entry_id=f"{event_id}:L{level}", event_id=event_id, affiliate_id=aff.id,
                buyer_id=buyer_id, level=level, recipient_tier=aff.tier, rate_pct=rate,
                base_amount=base, amount=_money(base * rate / 100), kind=kind,
                created_at=at, available_at=at + timedelta(days=self.hold_days))
            self.entries.append(entry)
            created.append(entry)
        return created

    def record_reversal(self, reversal_id, event_id, amount=None, kind="refund", at=None):
        """Offset commissions for a full or partial refund/chargeback. Idempotent on ``reversal_id``."""
        if kind not in REVERSAL_KINDS:
            raise ValueError(f"unknown reversal kind: {kind}")
        if reversal_id in self.reversals:
            return [e for e in self.entries if e.event_id == reversal_id]
        payment = self.payments.get(event_id)
        if payment is None:
            raise KeyError(event_id)
        remaining = payment.amount - payment.reversed_amount
        reverse = remaining if amount is None else _money(amount)
        if reverse <= 0 or reverse > remaining:
            raise ValueError("reversal exceeds remaining payment amount")
        self.reversals.add(reversal_id)
        payment.reversed_amount += reverse
        at = at or datetime.now(timezone.utc)
        created = []
        for orig in [e for e in self.entries if e.event_id == event_id]:
            entry = Entry(
                entry_id=f"{reversal_id}:L{orig.level}", event_id=reversal_id,
                affiliate_id=orig.affiliate_id, buyer_id=orig.buyer_id, level=orig.level,
                recipient_tier=orig.recipient_tier, rate_pct=orig.rate_pct,
                base_amount=-reverse, amount=-_money(reverse * orig.rate_pct / 100),
                kind=kind, created_at=at, available_at=at)
            self.entries.append(entry)
            created.append(entry)
        return created

    def balance(self, affiliate_id, as_of=None):
        """Return pending (in hold), available and reversed totals. Nothing is ever 'paid'."""
        as_of = as_of or datetime.now(timezone.utc)
        pending = available = reversed_ = Decimal("0")
        for e in self.entries:
            if e.affiliate_id != affiliate_id:
                continue
            if e.amount < 0:
                reversed_ += e.amount
                available += e.amount
            elif e.available_at > as_of:
                pending += e.amount
            else:
                available += e.amount
        return {"pending": pending, "available": available, "reversed": reversed_, "paid": Decimal("0")}

    def payout(self, *_args, **_kwargs):
        raise PayoutsDisabled("Affiliate payouts are disabled pending compliance, KYC/tax and founder approval")
