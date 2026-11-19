"""Seven-day Stripe trials. Email ownership and access are separate from a receipt."""

import asyncio
import hashlib
import time
import stripe
from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError
from db import db, now
from billing_periods import identity

TRIAL_DAYS = 7
TRIAL_TIERS = {"pro"}


def eligible_plan(plan):
    return (
        plan.get("tier", plan.get("id")) in TRIAL_TIERS
        and plan.get("interval") == "month"
        and plan.get("amount", 0) > 0
    )


def claim_key(email, mode):
    return mode + ":" + hashlib.sha256(email.strip().lower().encode()).hexdigest()


async def reserve(email, config, owner):
    key = claim_key(email, config["mode"])
    existing = await db.subscription_trials.find_one({"_id": key})
    if existing:
        if existing.get("used"):
            raise HTTPException(
                409,
                "This customer has already used a free trial. Sign in and choose a paid membership instead.",
            )
        sid = existing.get("session_id")
        if sid:
            session = await asyncio.to_thread(
                stripe.checkout.Session.retrieve, sid, api_key=config["key"]
            )
            if session.get("status") == "expired":
                await db.subscription_trials.delete_one(
                    {
                        "_id": key,
                        "owner": existing["owner"],
                        "used": False,
                        "session_id": sid,
                    }
                )
                existing = None
        if existing and existing["owner"] != owner:
            raise HTTPException(
                409,
                "A free-trial checkout is already in progress for this email. Continue in the original browser or sign in.",
            )
        if existing:
            return key
    try:
        await db.subscription_trials.insert_one(
            {"_id": key, "owner": owner, "used": False, "created_at": time.time()}
        )
    except DuplicateKeyError:
        raise HTTPException(
            409, "Free-trial checkout is being prepared. Please retry shortly."
        ) from None
    return key


async def attach(key, owner, session_id):
    result = await db.subscription_trials.update_one(
        {"_id": key, "owner": owner, "used": False},
        {"$set": {"session_id": session_id}},
    )
    if result.matched_count != 1:
        raise HTTPException(503, "Trial checkout reservation needs reconciliation")


def checkout_arguments(requested):
    if not requested:
        return {}
    return {
        "payment_method_collection": "always",
        "payment_method_types": ["card"],
        "custom_text": {
            "submit": {
                "message": "7-day free trial. Your selected membership renews automatically at the displayed price after the trial unless canceled. Cancel in KAOS billing before the trial ends."
            }
        },
    }


def subscription_arguments(metadata, requested):
    return {
        "metadata": metadata,
        **(
            {
                "trial_period_days": TRIAL_DAYS,
                "trial_settings": {
                    "end_behavior": {"missing_payment_method": "cancel"}
                },
            }
            if requested
            else {}
        ),
    }


async def verify(record, session, subscription, config):
    """Never accept no_payment_required as evidence for an ordinary paid checkout."""
    if not record.get("trial_key") or record.get("trial_days") != TRIAL_DAYS:
        raise HTTPException(409, "Trial checkout was not requested by this account")
    if (
        session.get("status") != "complete"
        or session.get("payment_status") not in ("paid", "no_payment_required")
        or (session.get("metadata") or {}).get("kaos_trial_days") != str(TRIAL_DAYS)
        or subscription.get("status") != "trialing"
    ):
        raise HTTPException(409, "Stripe has not confirmed this free trial")
    start, end = subscription.get("trial_start"), subscription.get("trial_end")
    if (
        type(start) not in (int, float)
        or type(end) not in (int, float)
        or not start <= now().timestamp() < end
        or end - start > TRIAL_DAYS * 86400 + 60
    ):
        raise HTTPException(409, "Trial dates are invalid or the trial has expired")
    customer = identity(subscription.get("customer"))
    if customer != identity(session.get("customer")):
        raise HTTPException(409, "Trial customer identity mismatch")
    pm = identity(subscription.get("default_payment_method"))
    if not pm:
        saved_customer = await asyncio.to_thread(
            stripe.Customer.retrieve, customer, api_key=config["key"]
        )
        if saved_customer.get("id") != customer:
            raise HTTPException(409, "Saved-card customer identity mismatch")
        pm = identity(
            (saved_customer.get("invoice_settings") or {}).get("default_payment_method")
        )
    if not pm:
        raise HTTPException(
            503, "Stripe is still confirming the saved card. Please retry."
        )
    method = await asyncio.to_thread(
        stripe.PaymentMethod.retrieve, pm, api_key=config["key"]
    )
    if method.get("type") != "card" or identity(method.get("customer")) != customer:
        raise HTTPException(409, "A verified saved card is required to start the trial")
    claim = await db.subscription_trials.find_one({"_id": record["trial_key"]})
    if (
        not claim
        or claim.get("owner") != record.get("trial_owner")
        or claim.get("session_id") != session.get("id")
    ):
        raise HTTPException(409, "Trial reservation does not match this checkout")
    if claim.get("used") and claim.get("session_id") != session.get("id"):
        raise HTTPException(409, "Trial already used")
    return int(end)


async def consume(record, session_id):
    result = await db.subscription_trials.update_one(
        {
            "_id": record["trial_key"],
            "owner": record["trial_owner"],
            "session_id": session_id,
        },
        {"$set": {"used": True, "confirmed_at": time.time()}},
    )
    if result.matched_count != 1:
        raise HTTPException(503, "Trial reservation needs reconciliation")


def trial_expired(user):
    from datetime import datetime, timezone

    value = user.get("pro_trial_ends_at") or user.get("membership_expires_at")
    if not value:
        return True
    try:
        end = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        return end <= now()
    except (ValueError, TypeError, AttributeError):
        return True


async def reminder(subscription, config):
    """Handle Stripe trial_will_end, normally about three days before trial end."""
    from html import escape
    import os
    from datetime import datetime, timezone
    from mail_delivery import send_account_email
    from billing_periods import iso

    sid = subscription.get("id")
    if not sid:
        raise HTTPException(409, "Missing subscription identity")
    canonical = await asyncio.to_thread(
        stripe.Subscription.retrieve, sid, api_key=config["key"]
    )
    if canonical.get("id") != sid:
        raise HTTPException(409, "Subscription identity mismatch")
    if canonical.get("status") != "trialing" or canonical.get("cancel_at_period_end"):
        return
    end = canonical.get("trial_end")
    if not isinstance(end, (int, float)) or end <= now().timestamp():
        return
    customer = identity(canonical.get("customer"))
    user = await db.users.find_one(
        {"stripe_customer_id": customer, "stripe_subscription_id": sid}
    )
    record = await db.subscriptions.find_one(
        {"stripe_subscription_id": sid, "userId": (user or {}).get("id")}
    )
    if not user or not record:
        raise HTTPException(503, "Trial account is still being linked; retry reminder")
    if record.get("trial_days") != TRIAL_DAYS:
        return
    key = sid + ":" + str(int(end))
    claim = await db.trial_reminders.find_one({"_id": key})
    if claim and claim.get("sent"):
        return
    try:
        result = await db.trial_reminders.update_one(
            {
                "_id": key,
                "$or": [{"until": {"$lt": time.time()}}, {"until": {"$exists": False}}],
            },
            {"$set": {"until": time.time() + 60}},
            upsert=True,
        )
    except DuplicateKeyError:
        raise HTTPException(503, "Reminder delivery in progress; retry") from None
    base = os.getenv("FRONTEND_URL", "").rstrip("/")
    if not base.startswith("https://"):
        raise HTTPException(503, "Account email URL is not configured")
    amount = f"{record.get('amount',0)/100:.2f} {record.get('currency','usd').upper()}"
    date = datetime.fromtimestamp(end, timezone.utc).strftime("%B %d, %Y at %H:%M UTC")
    body = f'<p>Your KAOS Pro free trial ends {escape(date)}.</p><p>Your membership renews at {escape(amount)} per {escape(record.get("interval","month"))} unless canceled before then.</p><p><a href="{escape(base)}/dashboard/subscription">Manage or cancel your subscription</a></p>'
    if not await send_account_email(
        user["email"], "Your KAOS Pro trial is ending soon", body
    ):
        raise HTTPException(503, "Reminder email delivery failed; retry")
    await db.trial_reminders.update_one(
        {"_id": key}, {"$set": {"sent": True, "sent_at": iso(now().timestamp())}}
    )
