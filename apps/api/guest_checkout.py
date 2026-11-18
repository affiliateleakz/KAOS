"""Stripe payment before KAOS account creation. Receipt cookies are not login tokens."""

import asyncio, hashlib, hmac, secrets, time
from datetime import timedelta
from urllib.parse import urlencode
from uuid import uuid4
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field
from pymongo.errors import DuplicateKeyError
import stripe
from db import db, now, now_iso
from auth import get_current_user
import routes_billing as billing
import subscription_trial as trials
from stripe_runtime import active_configuration
from mail_delivery import account_mail_ready

router = APIRouter(prefix="/api/billing", tags=["payment-first"])
COOKIE = "kaos_guest_checkout"


class Intent(BaseModel):
    name: str = Field(default="", max_length=120)
    start_trial: bool = False
    plan_id: str = Field(min_length=1, max_length=64)
    email: EmailStr
    refCode: str | None = Field(default=None, max_length=128)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def cookie_value(request):
    value = request.cookies.get(COOKIE, "")
    if "." not in value:
        return None, None
    pid, secret = value.split(".", 1)
    if len(pid) != 32 or len(secret) > 100:
        return None, None
    return pid, secret


async def owned(request, session_id=None):
    pid, secret = cookie_value(request)
    row = await db.guest_purchases.find_one({"_id": pid}) if pid else None
    if not row or not hmac.compare_digest(row.get("secret_hash", ""), digest(secret)):
        raise HTTPException(
            403,
            "Return to the browser where you started checkout, or sign in and contact support with your Stripe receipt",
        )
    if session_id and row.get("session_id") != session_id:
        raise HTTPException(404, "Purchase not found")
    return row


def set_cookie(response, pid, secret):
    response.set_cookie(
        COOKIE,
        pid + "." + secret,
        max_age=7 * 86400,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/api/billing",
    )
    response.headers["Cache-Control"] = "private, no-store"


async def public_rate(request):
    # Bound anonymous processor-object creation; no raw IP address is stored.
    host = request.client.host if request.client else "unknown"
    await db.guest_checkout_limits.create_index("expires_at", expireAfterSeconds=0)
    key = digest(host + ":" + str(int(time.time() // 300)))
    try:
        await db.guest_checkout_limits.update_one(
            {"_id": key, "count": {"$lt": 30}},
            {
                "$inc": {"count": 1},
                "$setOnInsert": {"expires_at": now() + timedelta(hours=1)},
            },
            upsert=True,
        )
    except DuplicateKeyError:
        raise HTTPException(
            429, "Too many checkout attempts. Please wait before retrying"
        ) from None


@router.post("/guest-intent")
async def intent(req: Intent, request: Request, response: Response):
    config = await active_configuration()
    if not account_mail_ready():
        raise HTTPException(
            503,
            "New membership checkout is temporarily unavailable. Please try again later",
        )
    await public_rate(request)
    plan = next(
        (
            p
            for p in await billing.get_plans()
            if p.get("id") == req.plan_id
            and p.get("enabled", True)
            and p.get("amount", 0) > 0
        ),
        None,
    )
    if not plan:
        raise HTTPException(400, "Choose a current paid membership")
    if req.start_trial and not trials.eligible_plan(plan):
        raise HTTPException(
            400, "The 7-day free trial is available on Pro monthly only"
        )
    email = str(req.email).strip().lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(
            409,
            {
                "code": "SIGN_IN_REQUIRED",
                "message": "Sign in to continue with this email. Your selected membership will be retained.",
            },
        )
    # Startup hooks need not run on Passenger. Establish uniqueness before accepting a payment.
    try:
        await db.users.create_index("email", unique=True)
    except Exception:
        raise HTTPException(
            503, "Account setup is temporarily unavailable; no payment has been started"
        ) from None
    pid, secret = cookie_value(request)
    prior = await db.guest_purchases.find_one({"_id": pid}) if pid else None
    ours = prior and hmac.compare_digest(prior.get("secret_hash", ""), digest(secret))
    if ours and prior.get("stripe_mode") == config["mode"]:
        same = (
            bool(prior.get("trial_requested")) == req.start_trial
            and prior["email"] == email
            and prior["plan"]["id"] == plan["id"]
            and prior["plan"]["amount"] == plan["amount"]
            and prior["plan"].get("currency") == plan.get("currency")
            and prior["plan"]["interval"] == plan["interval"]
        )
        if same and prior.get("session_id"):
            previous = await asyncio.to_thread(
                stripe.checkout.Session.retrieve,
                prior["session_id"],
                api_key=config["key"],
            )
            same = previous.get("status") != "expired"
        if same:
            set_cookie(response, pid, secret)
            return {"ready": True}
        if prior.get("state") == "CREATING" and not prior.get("session_id"):
            raise HTTPException(
                409,
                "Your previous checkout is being prepared. Retry that membership before changing plans",
            )
        if prior.get("session_id"):
            session = await asyncio.to_thread(
                stripe.checkout.Session.retrieve,
                prior["session_id"],
                api_key=config["key"],
            )
            if session.get("status") == "complete":
                raise HTTPException(
                    409,
                    "Finish setting up the membership you already purchased before starting another checkout",
                )
            if session.get("status") == "open":
                await asyncio.to_thread(
                    stripe.checkout.Session.expire,
                    prior["session_id"],
                    api_key=config["key"],
                )
        await db.guest_purchase_emails.delete_one(
            {"_id": prior["email_lock"], "purchase_id": pid}
        )
    lock = digest(config["mode"] + ":" + email)
    existing = await db.guest_purchase_emails.find_one({"_id": lock})
    if existing:
        old = await db.guest_purchases.find_one({"_id": existing["purchase_id"]})
        # Lost intent responses have not reached Stripe and may be replaced after two minutes.
        removable = (
            old
            and old.get("state") == "INTENT"
            and time.time() - old.get("created_at_s", 0) > 120
        )
        if old and old.get("session_id"):
            previous = await asyncio.to_thread(
                stripe.checkout.Session.retrieve,
                old["session_id"],
                api_key=config["key"],
            )
            removable = previous.get("status") == "expired"
        if not removable:
            raise HTTPException(
                409,
                "A checkout for this email already exists. Use the original browser or contact support with your receipt",
            )
        await db.guest_purchase_emails.delete_one(
            {"_id": lock, "purchase_id": existing["purchase_id"]}
        )
    pid = uuid4().hex
    secret = secrets.token_urlsafe(32)
    row = {
        "_id": pid,
        "email": email,
        "name": req.name.strip(),
        "trial_requested": req.start_trial,
        "secret_hash": digest(secret),
        "plan": plan,
        "stripe_mode": config["mode"],
        "email_lock": lock,
        "refCode": req.refCode,
        "state": "INTENT",
        "created_at_s": time.time(),
        "createdAt": now_iso(),
    }
    # Nothing on this endpoint creates a KAOS user, Stripe customer, or charge.
    await db.guest_purchases.insert_one(row)
    try:
        await db.guest_purchase_emails.insert_one({"_id": lock, "purchase_id": pid})
    except DuplicateKeyError:
        raise HTTPException(
            409, "Checkout is already being prepared for this email"
        ) from None
    set_cookie(response, pid, secret)
    return {"ready": True}


@router.post("/guest-checkout")
async def checkout(request: Request, response: Response):
    config = await active_configuration()
    purchase = await owned(request)
    if purchase["stripe_mode"] != config["mode"]:
        raise HTTPException(
            409, "Checkout environment changed. Contact support before retrying"
        )
    response.headers["Cache-Control"] = "private, no-store"
    async with billing._checkout_lock("guest:" + purchase["_id"], config["mode"]):
        purchase = await db.guest_purchases.find_one({"_id": purchase["_id"]})
        if purchase.get("session_id"):
            old = await asyncio.to_thread(
                stripe.checkout.Session.retrieve,
                purchase["session_id"],
                api_key=config["key"],
            )
            if old.get("status") == "complete":
                return {"completed": True, "session_id": old["id"]}
            if old.get("status") == "open":
                return {"checkout_url": old["url"], "session_id": old["id"]}
            raise HTTPException(
                409,
                "Checkout expired. Choose the membership again to start a fresh payment",
            )
        started = purchase.get("checkout_started_s") or time.time()
        if time.time() - started > 23 * 3600:
            raise HTTPException(
                409,
                "An interrupted payment needs support review before another checkout can be created",
            )
        await db.guest_purchases.update_one(
            {"_id": purchase["_id"]},
            {"$set": {"state": "CREATING", "checkout_started_s": started}},
        )
        customer = purchase.get("customer_id")
        if not customer:
            created = await asyncio.to_thread(
                stripe.Customer.create,
                api_key=config["key"],
                idempotency_key="kaos-guest-customer-"
                + config["mode"]
                + purchase["_id"],
                email=purchase["email"],
                metadata={"guest_purchase_id": purchase["_id"]},
            )
            customer = created.id
            await db.guest_purchases.update_one(
                {"_id": purchase["_id"]}, {"$set": {"customer_id": customer}}
            )
        plan = purchase["plan"]
        price = await billing._price(plan, config)
        requested = bool(purchase.get("trial_requested"))
        trial_fields = {}
        if requested:
            key = await trials.reserve(purchase["email"], config, purchase["_id"])
            trial_fields = {
                "trial_key": key,
                "trial_owner": purchase["_id"],
                "trial_days": trials.TRIAL_DAYS,
            }
            await db.guest_purchases.update_one(
                {"_id": purchase["_id"]}, {"$set": trial_fields}
            )
        metadata = {
            "guest_purchase_id": purchase["_id"],
            "plan_id": plan["id"],
            **({"kaos_trial_days": str(trials.TRIAL_DAYS)} if requested else {}),
        }
        from os import environ

        base = environ["FRONTEND_URL"].rstrip("/")
        session = await asyncio.to_thread(
            stripe.checkout.Session.create,
            api_key=config["key"],
            idempotency_key="kaos-guest-session-" + config["mode"] + purchase["_id"],
            mode="subscription",
            customer=customer,
            **({} if requested else {"payment_method_types": ["card"]}),
            **trials.checkout_arguments(requested),
            line_items=[{"price": price, "quantity": 1}],
            metadata=metadata,
            subscription_data=trials.subscription_arguments(metadata, requested),
            success_url=base + "/payment/complete?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=base
            + "/payment/cancel?"
            + urlencode({"plan": plan["id"], **({"trial": "1"} if requested else {})}),
        )
        if requested:
            await trials.attach(key, purchase["_id"], session.id)
        await db.guest_purchases.update_one(
            {"_id": purchase["_id"]},
            {"$set": {"session_id": session.id, "state": "CHECKOUT"}},
        )
        await db.subscriptions.update_one(
            {"_id": "guest:" + purchase["_id"]},
            {
                "$setOnInsert": {
                    **trial_fields,
                    "id": "guest:" + purchase["_id"],
                    "guest_purchase_id": purchase["_id"],
                    "session_id": session.id,
                    "planId": plan["id"],
                    "lookup_key": plan["lookup_key"],
                    "amount": plan["amount"],
                    "currency": plan["currency"],
                    "interval": plan["interval"],
                    "state": "initiated",
                    "stripe_customer_id": customer,
                    "stripe_mode": config["mode"],
                    "createdAt": now_iso(),
                    "updatedAt": now_iso(),
                }
            },
            upsert=True,
        )
        return {"checkout_url": session.url, "session_id": session.id}


async def verified_payment(purchase):
    config = await active_configuration()
    if config["mode"] != purchase["stripe_mode"]:
        raise HTTPException(409, "Purchase environment needs review")
    session = await asyncio.to_thread(
        stripe.checkout.Session.retrieve, purchase["session_id"], api_key=config["key"]
    )
    meta = session.get("metadata") or {}
    if (
        session.get("id") != purchase["session_id"]
        or billing.identity(session.get("customer")) != purchase["customer_id"]
        or meta.get("guest_purchase_id") != purchase["_id"]
        or meta.get("plan_id") != purchase["plan"]["id"]
    ):
        raise HTTPException(409, "Payment identity needs review")
    if session.get("status") != "complete" or session.get("payment_status") not in (
        "paid",
        "no_payment_required",
    ):
        return None
    detail = session.get("customer_details") or {}
    if str(detail.get("email", "")).lower() != purchase["email"]:
        raise HTTPException(409, "Receipt email needs review")
    sub = billing.identity(session.get("subscription"))
    invoice_id = billing.identity(session.get("invoice"))
    if not sub or not invoice_id:
        raise HTTPException(503, "Payment confirmation is still processing")
    subscription = await billing._verified_subscription(sub, purchase["customer_id"])
    if (
        subscription.get("status") not in ("active", "trialing")
        or billing.period_end(subscription) <= now().timestamp()
    ):
        raise HTTPException(409, "Subscription needs support review")
    if (
        session.get("payment_status") == "no_payment_required"
        or subscription.get("status") == "trialing"
    ):
        await trials.verify(purchase, session, subscription, config)
    invoice = await asyncio.to_thread(
        stripe.Invoice.retrieve, invoice_id, api_key=config["key"]
    )
    if (
        invoice.get("status") != "paid"
        or billing.identity(invoice.get("customer")) != purchase["customer_id"]
        or billing.subscription_id(invoice) != sub
    ):
        raise HTTPException(409, "Invoice payment needs review")
    charges = await asyncio.to_thread(
        stripe.Charge.list,
        customer=purchase["customer_id"],
        limit=100,
        api_key=config["key"],
    )
    if charges.get("has_more") or any(
        c.get("refunded") or c.get("amount_refunded", 0) > 0 or c.get("disputed")
        for c in charges.get("data", [])
    ):
        raise HTTPException(409, "Payment refund or dispute needs support review")
    if invoice.get("amount_paid", 0) > 0 and not any(
        c.get("paid") is True and c.get("status") == "succeeded"
        for c in charges.get("data", [])
    ):
        raise HTTPException(503, "Card payment confirmation is still processing")
    return {"session": session, "subscription": sub, "invoice": invoice}


async def invite(purchase, user, force=False):
    import routes_auth as auth

    if user.get("password_hash") or user.get("auth_provider") != "stripe_checkout":
        return False
    if purchase.get("invite_sent") and not force:
        return True
    claim = uuid4().hex
    changed = await db.guest_purchases.update_one(
        {
            "_id": purchase["_id"],
            "$or": [
                {"mail_until": {"$lt": time.time()}},
                {"mail_until": {"$exists": False}},
            ],
        },
        {"$set": {"mail_claim": claim, "mail_until": time.time() + 60}},
    )
    if changed.modified_count != 1:
        return bool(purchase.get("invite_sent"))
    token = auth.gen_token()
    await db.password_reset_tokens.insert_one(
        {
            "_id": auth.hash_token(token),
            "token_hash": auth.hash_token(token),
            "user_id": user["id"],
            "email": user["email"],
            "expires_at": now() + timedelta(hours=1),
            "used": False,
            "checkout_setup": True,
        }
    )
    sent = await auth.send_password_reset_email(
        user["email"], token, account_setup=True
    )
    await db.guest_purchases.update_one(
        {"_id": purchase["_id"], "mail_claim": claim},
        {"$set": {"invite_sent": sent, "mail_until": time.time() + 60}},
    )
    return sent


async def fulfill(purchase, viewer=None):
    async with billing._checkout_lock(
        "fulfill:" + purchase["_id"], purchase["stripe_mode"]
    ):
        fresh = await db.guest_purchases.find_one({"_id": purchase["_id"]})
        return await _fulfill(fresh, viewer)


async def _fulfill(purchase, viewer=None):
    if purchase.get("state") == "ACTIVE":
        user = await db.users.find_one({"id": purchase["user_id"]})
        return {
            "state": "active",
            "setupRequired": bool(
                user
                and not user.get("password_hash")
                and user.get("auth_provider") == "stripe_checkout"
            ),
            "emailSent": bool(purchase.get("invite_sent")),
            "receiptEmail": purchase["email"],
            "trial": bool(purchase.get("trial_requested")),
            "trialEndsAt": (user or {}).get("pro_trial_ends_at"),
        }
    verified = await verified_payment(purchase)
    if not verified:
        return {"state": "pending"}
    import routes_auth as auth

    # The first KAOS account write occurs here, only after canonical paid verification.
    user = await db.users.find_one({"email": purchase["email"]})
    if not user:
        doc = await auth._new_user_doc(
            purchase["email"],
            purchase.get("name")
            or (verified["session"].get("customer_details") or {}).get("name")
            or purchase["email"],
            provider="stripe_checkout",
        )
        doc.update(
            _id="guest-user:" + purchase["_id"],
            checkout_purchase_id=purchase["_id"],
            referredByCode=purchase.get("refCode"),
            requested_membership_plan=purchase["plan"]["id"],
        )
        try:
            await db.users.insert_one(doc)
        except DuplicateKeyError:
            pass
        user = await db.users.find_one({"email": purchase["email"]})
    if not user:
        raise HTTPException(503, "Paid account setup is still processing")
    own_new = user.get("checkout_purchase_id") == purchase["_id"]
    if not own_new and (not viewer or viewer["id"] != user["id"]):
        return {"state": "signin_required"}
    if (
        user.get("stripe_subscription_id")
        and user["stripe_subscription_id"] != verified["subscription"]
    ):
        raise HTTPException(
            409,
            "An existing subscription needs support review; another membership will not be attached",
        )
    await db.guest_purchases.update_one(
        {"_id": purchase["_id"]}, {"$set": {"user_id": user["id"], "state": "PAID"}}
    )
    # Repair the local relationship even if the first response was lost after
    # Stripe created the session but before its local subscription row was saved.
    plan = purchase["plan"]
    await db.subscriptions.update_one(
        {"_id": "guest:" + purchase["_id"]},
        {
            "$set": {
                "userId": user["id"],
                "stripe_subscription_id": verified["subscription"],
            },
            "$setOnInsert": {
                **{
                    k: purchase[k]
                    for k in ("trial_key", "trial_owner", "trial_days")
                    if k in purchase
                },
                "id": "guest:" + purchase["_id"],
                "guest_purchase_id": purchase["_id"],
                "session_id": purchase["session_id"],
                "planId": plan["id"],
                "lookup_key": plan["lookup_key"],
                "amount": plan["amount"],
                "currency": plan["currency"],
                "interval": plan["interval"],
                "state": "initiated",
                "stripe_customer_id": purchase["customer_id"],
                "stripe_mode": purchase["stripe_mode"],
                "createdAt": now_iso(),
                "updatedAt": now_iso(),
            },
        },
        upsert=True,
    )
    await billing._activate(
        user["id"],
        purchase["plan"]["id"],
        purchase["customer_id"],
        verified["subscription"],
        purchase["session_id"],
    )
    # Initial/renewal invoices that arrived before an exceptional account-link race are replayed by invoice identity.
    pending = await db.guest_invoice_events.find(
        {"purchase_id": purchase["_id"]}
    ).to_list(100)
    config = await active_configuration()
    for event in pending:
        invoice = await asyncio.to_thread(
            stripe.Invoice.retrieve, event["invoice_id"], api_key=config["key"]
        )
        await billing._paid_invoice(invoice)
        await db.guest_invoice_events.delete_one({"_id": event["_id"]})
    user = await db.users.find_one({"id": user["id"]})
    sent = await invite(purchase, user)
    await db.guest_purchases.update_one(
        {"_id": purchase["_id"]}, {"$set": {"state": "ACTIVE"}}
    )
    return {
        "state": "active",
        "setupRequired": not bool(user.get("password_hash"))
        and user.get("auth_provider") == "stripe_checkout",
        "emailSent": sent,
        "receiptEmail": purchase["email"],
        "trial": bool(purchase.get("trial_requested")),
        "trialEndsAt": (user or {}).get("pro_trial_ends_at"),
    }


async def from_webhook(session_id):
    purchase = await db.guest_purchases.find_one({"session_id": session_id})
    if not purchase:
        raise HTTPException(503, "Guest checkout receipt is not ready; retry")
    return await fulfill(purchase)


async def guest_invoice(invoice):
    purchase = await db.guest_purchases.find_one(
        {"customer_id": billing.identity(invoice.get("customer"))}
    )
    if not purchase:
        return False
    if purchase.get("user_id"):
        return False
    await db.guest_invoice_events.update_one(
        {"_id": invoice["id"]},
        {"$setOnInsert": {"purchase_id": purchase["_id"], "invoice_id": invoice["id"]}},
        upsert=True,
    )
    await fulfill(purchase)
    return True


@router.get("/guest-status/{session_id}")
async def status(session_id: str, request: Request, response: Response):
    response.headers["Cache-Control"] = "private, no-store"
    purchase = await owned(request, session_id)
    try:
        viewer = await get_current_user(request)
    except HTTPException as exc:
        if exc.status_code != 401:
            raise
        viewer = None
    return await fulfill(purchase, viewer)


@router.post("/guest-resend/{session_id}")
async def resend(session_id: str, request: Request):
    purchase = await owned(request, session_id)
    if purchase.get("state") != "ACTIVE" or not purchase.get("user_id"):
        raise HTTPException(409, "Payment must be confirmed before account setup")
    user = await db.users.find_one({"id": purchase["user_id"]})
    return {"sent": await invite(purchase, user, True)}


@router.post("/guest-cancel/{session_id}")
async def cancel_trial_from_receipt(
    session_id: str, request: Request, response: Response
):
    """Allow the buyer to stop renewal even before the setup email is delivered."""
    response.headers["Cache-Control"] = "private, no-store"
    purchase = await owned(request, session_id)
    if not purchase.get("trial_requested") or purchase.get("state") != "ACTIVE":
        raise HTTPException(409, "A confirmed trial receipt is required")
    from stripe_runtime import configuration

    config = await configuration()
    if not config["ready"] or config["mode"] != purchase["stripe_mode"]:
        raise HTTPException(503, "Billing management is temporarily unavailable")
    record = await db.subscriptions.find_one(
        {"session_id": session_id, "guest_purchase_id": purchase["_id"]}
    )
    sub_id = (record or {}).get("stripe_subscription_id")
    if not sub_id:
        raise HTTPException(503, "Trial subscription is still being linked")
    subscription = await asyncio.to_thread(
        stripe.Subscription.retrieve, sub_id, api_key=config["key"]
    )
    if (
        billing.identity(subscription.get("customer")) != purchase["customer_id"]
        or subscription.get("id") != sub_id
    ):
        raise HTTPException(409, "Trial subscription identity mismatch")
    if subscription.get("status") == "canceled":
        return {"cancelAtPeriodEnd": True}
    if subscription.get("status") != "trialing":
        raise HTTPException(409, "Sign in to manage your current paid subscription")
    result = await asyncio.to_thread(
        stripe.Subscription.modify,
        sub_id,
        cancel_at_period_end=True,
        api_key=config["key"],
        idempotency_key="kaos-trial-cancel-" + purchase["_id"],
    )
    if result.get("cancel_at_period_end") is not True:
        raise HTTPException(
            503, "Cancellation is not confirmed; retry or contact support"
        )
    return {"cancelAtPeriodEnd": True}
