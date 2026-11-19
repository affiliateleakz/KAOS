"""Affiliate participation requires a current paid membership, never a free trial."""

from datetime import datetime, timezone
from fastapi import HTTPException


def paid_member(user):
    if (
        not user
        or user.get("account_status", "active") in ("suspended", "banned", "deleted")
        or user.get("membership_status") != "ACTIVE"
    ):
        return False
    # Canonical Stripe billing sets this link only on verified activation. Trial status never qualifies.
    if (
        not isinstance(user.get("stripe_subscription_id"), str)
        or not user["stripe_subscription_id"]
    ):
        return False
    try:
        expiry = datetime.fromisoformat(
            user.get("membership_expires_at", "").replace("Z", "+00:00")
        )
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        return expiry > datetime.now(timezone.utc)
    except (ValueError, AttributeError, TypeError):
        return False


def require_paid_member(user):
    if not paid_member(user):
        raise HTTPException(
            403,
            "Affiliate access requires an active paid membership. Free trials do not include affiliate access or commissions.",
        )
