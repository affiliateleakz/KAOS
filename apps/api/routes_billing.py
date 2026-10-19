import logging
import os
import stripe
from fastapi import APIRouter, HTTPException, Depends, Request
from db import db, new_id, now, now_iso, clean
from auth import get_current_user
from services import get_setting, set_setting, audit_log
from models import CheckoutReq

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/billing", tags=["billing"])
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY") or None
WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

# Monthly billing only. Free is the tier of every account without a paid plan (not sold via checkout).
DEFAULT_PLANS = [
    {"id": "pro", "name": "Pro", "lookup_key": "membership_pro_monthly", "amount": 4900,
     "currency": "usd", "interval": "month", "deviceLimit": 3, "tier": "pro",
     "features": ["KAOS Trading Bot", "KAOS Strategy mode", "Scanners", "AI insights", "Cloud Strategies", "Community", "3 Devices"],
     "entitlements": {"botAccess": True, "modes": ["STRATEGY"], "connectors": ["pocket_option"], "scanners": True,
                      "aiInsights": True, "cloudStrategies": True, "community": True, "premiumTools": False, "deviceLimit": 3,
                      "chartLimit": 4}},
    {"id": "ultimate", "name": "Ultimate", "lookup_key": "membership_ultimate_monthly", "amount": 14900,
     "currency": "usd", "interval": "month", "deviceLimit": 5, "tier": "ultimate",
     "features": ["Everything in Pro", "KAOS AI mode", "Strategy + AI mode", "Premium Tools", "5 Devices"],
     "entitlements": {"botAccess": True, "modes": ["STRATEGY", "AI", "STRATEGY_AI"], "connectors": ["pocket_option"],
                      "scanners": True, "aiInsights": True, "cloudStrategies": True, "community": True,
                      "premiumTools": True, "deviceLimit": 5, "chartLimit": 4}},
]
# Members who subscribed under the retired plan ids keep working.
LEGACY_PLAN_IDS = {"monthly": "pro", "yearly": "ultimate"}


def find_plan(plans, plan_id):
    plan_id = LEGACY_PLAN_IDS.get(plan_id, plan_id)
    return next((p for p in plans if p["id"] == plan_id), None)


async def get_plans():
    plans = await get_setting("plans")
    return plans or DEFAULT_PLANS


@router.get("/plans")
async def list_plans():
    return await get_plans()


@router.post("/checkout")
async def checkout(req: CheckoutReq, user: dict = Depends(get_current_user)):
    plans = await get_plans()
    plan = next((p for p in plans if p["lookup_key"] == req.lookup_key), None)
    if not plan:
        raise HTTPException(status_code=400, detail="Unknown plan")
    customer_id = user.get("stripe_customer_id")
    if not customer_id:
        cust = stripe.Customer.create(email=user["email"], name=user.get("name"),
                                      metadata={"user_id": user["id"]})
        customer_id = cust.id
        await db.users.update_one({"id": user["id"]}, {"$set": {"stripe_customer_id": customer_id}})
    price = stripe.Price.create(unit_amount=plan["amount"], currency=plan["currency"],
                                recurring={"interval": plan["interval"]},
                                product_data={"name": f"Trading Platform {plan['name']}"})
    session = stripe.checkout.Session.create(
        mode="subscription", customer=customer_id,
        line_items=[{"price": price.id, "quantity": 1}],
        success_url=f"{req.origin_url}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{req.origin_url}/payment/cancel",
        metadata={"user_id": user["id"], "plan_id": plan["id"], "lookup_key": plan["lookup_key"]})
    await db.subscriptions.insert_one({
        "id": new_id("sub"), "userId": user["id"], "session_id": session.id,
        "planId": plan["id"], "lookup_key": plan["lookup_key"], "amount": plan["amount"],
        "state": "initiated", "stripe_customer_id": customer_id, "stripe_subscription_id": None,
        "createdAt": now_iso(), "updatedAt": now_iso()})
    return {"checkout_url": session.url, "session_id": session.id}


@router.get("/status/{session_id}")
async def status(session_id: str, user: dict = Depends(get_current_user)):
    rec = await db.subscriptions.find_one({"session_id": session_id, "userId": user["id"]})
    if not rec:
        raise HTTPException(status_code=404, detail="Not found")
    if rec.get("state") not in ("active", "completed"):
        try:
            s = stripe.checkout.Session.retrieve(session_id)
            if (s.payment_status == "paid" and s.status == "complete"
                    and s.get("customer") == rec.get("stripe_customer_id")
                    and s.get("metadata", {}).get("user_id") == user["id"]):
                await _activate(rec["userId"], rec["planId"], s.get("customer"), s.get("subscription"), session_id)
                rec = await db.subscriptions.find_one({"session_id": session_id})
        except stripe.error.StripeError:
            pass
    return {"session_id": session_id, "state": rec.get("state"),
            "membershipStatus": rec.get("membershipStatus", "PENDING")}


async def _activate(user_id, plan_id, customer, subscription, session_id):
    plans = await get_plans()
    plan = find_plan(plans, plan_id)
    from datetime import timedelta
    days = 365 if (plan and plan.get("interval") == "year") else 30
    expires = (now() + timedelta(days=days)).isoformat()
    await db.subscriptions.update_one({"session_id": session_id},
        {"$set": {"state": "active", "membershipStatus": "ACTIVE",
                  "stripe_subscription_id": subscription, "updatedAt": now_iso()}})
    await db.users.update_one({"id": user_id},
        {"$set": {"membership_status": "ACTIVE", "membership_plan": plan_id,
                  "membership_expires_at": expires, "stripe_subscription_id": subscription,
                  "stripe_customer_id": customer, "onboarding_step": 7, "updated_at": now_iso()}})
    if plan:
        try:
            from routes_affiliate import record_commission
            cust_user = await db.users.find_one({"id": user_id})
            await record_commission(cust_user, plan, "purchase", event_id=f"checkout:{session_id}")
        except Exception:
            logger.exception("affiliate commission failed for %s", session_id)


@router.post("/portal")
async def billing_portal(req: CheckoutReq, user: dict = Depends(get_current_user)):
    if not user.get("stripe_customer_id"):
        raise HTTPException(status_code=400, detail="No billing account")
    session = stripe.billing_portal.Session.create(customer=user["stripe_customer_id"],
                                                    return_url=f"{req.origin_url}/dashboard/subscription")
    return {"url": session.url}


@router.post("/cancel")
async def cancel(user: dict = Depends(get_current_user)):
    sub_id = user.get("stripe_subscription_id")
    if sub_id:
        try:
            stripe.Subscription.modify(sub_id, cancel_at_period_end=True)
        except stripe.error.StripeError:
            pass
    await db.users.update_one({"id": user["id"]}, {"$set": {"cancel_at_period_end": bool(sub_id), "updated_at": now_iso()}})
    return {"canceled": True}


# Stripe webhook (authoritative, idempotent, signature-verified)
webhook_router = APIRouter(tags=["billing"])


@webhook_router.post("/api/stripe/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(payload, sig, WEBHOOK_SECRET)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid signature")
    # idempotency
    if await db.webhook_events.find_one({"event_id": event["id"]}):
        return {"status": "duplicate"}
    await db.webhook_events.insert_one({"event_id": event["id"], "type": event["type"], "createdAt": now_iso()})
    obj = event["data"]["object"]
    t = event["type"]
    if t == "checkout.session.completed":
        meta = obj.get("metadata", {})
        if meta.get("user_id"):
            await _activate(meta["user_id"], meta.get("plan_id"), obj.get("customer"), obj.get("subscription"), obj["id"])
    elif t == "invoice.payment_failed":
        cust = obj.get("customer")
        u = await db.users.find_one({"stripe_customer_id": cust})
        if u:
            await db.users.update_one({"id": u["id"]}, {"$set": {"membership_status": "PAST_DUE", "updated_at": now_iso()}})
    elif t == "customer.subscription.deleted":
        cust = obj.get("customer")
        u = await db.users.find_one({"stripe_customer_id": cust})
        if u:
            await db.users.update_one({"id": u["id"]}, {"$set": {"membership_status": "EXPIRED", "updated_at": now_iso()}})
            try:
                from routes_affiliate import reverse_commission
                await reverse_commission(u["id"], "subscription_canceled")
            except Exception:
                pass
    elif t == "invoice.paid":
        cust = obj.get("customer")
        u = await db.users.find_one({"stripe_customer_id": cust})
        if u and u.get("membership_status") == "PAST_DUE":
            await db.users.update_one({"id": u["id"]}, {"$set": {"membership_status": "ACTIVE", "updated_at": now_iso()}})
        if u and obj.get("billing_reason") == "subscription_cycle" and obj.get("amount_paid"):
            plan = find_plan(await get_plans(), u.get("membership_plan"))
            if plan:
                try:
                    from routes_affiliate import record_commission
                    await record_commission(u, plan, "renewal", event_id=f"invoice:{obj['id']}",
                                            amount_cents=obj["amount_paid"])
                except Exception:
                    logger.exception("affiliate renewal commission failed for %s", obj["id"])
    elif t in ("charge.refunded", "charge.dispute.created"):
        await _reverse_for_charge(obj, "chargeback" if t == "charge.dispute.created" else "refund")
    return {"status": "ok"}


async def _reverse_for_charge(obj, reason):
    """Offset affiliate commissions for a refunded or disputed charge (incremental for partial refunds)."""
    charge_id = obj.get("charge") if reason == "chargeback" else obj.get("id")
    u = await db.users.find_one({"stripe_customer_id": obj.get("customer")}) if obj.get("customer") else None
    pay = await db.affiliate_ledger_payments.find_one({"event_id": f"invoice:{obj.get('invoice')}"}) \
        if obj.get("invoice") else None
    if not pay and u:
        pay = await db.affiliate_ledger_payments.find_one({"buyer_id": u["id"]}, sort=[("at", -1)])
    if not pay:
        return
    from decimal import Decimal
    remaining = int((Decimal(pay["amount"]) - Decimal(pay["reversed_amount"])) * 100)
    if reason == "chargeback":
        cents = min(int(obj.get("amount") or 0), remaining)
    else:
        already = int(Decimal(pay["reversed_amount"]) * 100)
        cents = min(int(obj.get("amount_refunded") or 0) - already, remaining)
    if cents <= 0:
        return
    try:
        from routes_affiliate import reverse_commission
        await reverse_commission(pay["buyer_id"], reason, event_id=pay["event_id"], amount_cents=cents,
                                 reversal_id=f"{reason}:{charge_id}:{cents}")
    except Exception:
        logger.exception("affiliate reversal failed for %s", charge_id)
