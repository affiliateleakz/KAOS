import logging
import asyncio
import hashlib
import json
import time
from urllib.parse import urlencode
from uuid import uuid4
from contextlib import asynccontextmanager
from pymongo.errors import DuplicateKeyError
from copy import deepcopy
import os
import stripe
import subscription_trial as trials
from fastapi import APIRouter, HTTPException, Depends, Request, Response
from db import db, new_id, now, now_iso, clean
from auth import get_current_user
from services import get_setting, set_setting, audit_log
from models import CheckoutReq
from services_trading import FREE_ENTITLEMENTS
from stripe_runtime import active_configuration, availability
from billing_periods import identity, period_end, invoice_period_end, subscription_id, iso

logger = logging.getLogger(__name__)
stripe.default_http_client = stripe.RequestsClient(timeout=(5,15))
stripe.max_network_retries = 0

router = APIRouter(prefix="/api/billing", tags=["billing"])


@router.get('/availability')
async def billing_availability():
    return await availability()

# Paid tiers offer monthly and annual billing. Free is not sold through checkout.
DEFAULT_PLANS = [
    {"id": "pro", "name": "Pro", "lookup_key": "membership_pro_monthly", "amount": 2995,
     "currency": "usd", "interval": "month", "deviceLimit": 3, "tier": "pro",
     "features": ["KAOS Trading Bot", "KAOS Strategy mode", "Scanners", "AI insights", "Personal AI starts untrained; train your own model", "Cloud Strategies", "Community", "Up to 4 broker chart slots", "3 Devices"],
     "entitlements": {"botAccess": True, "modes": ["STRATEGY", "AI", "STRATEGY_AI"], "connectors": ["pocket_option"], "scanners": True,
                      "aiInsights": True, "aiTraining": True, "pretrainedModels": False, "cloudStrategies": True, "community": True, "premiumTools": False, "deviceLimit": 3,
                      "chartLimit": 4}},
    {"id": "ultimate", "name": "Ultimate", "lookup_key": "membership_ultimate_monthly", "amount": 9995,
     "currency": "usd", "interval": "month", "deviceLimit": 5, "tier": "ultimate", "recommended": True,
     "features": ["Everything in Pro", "Published pretrained bot model access", "AI / Strategy + AI eligibility (after independent validation)", "Premium Tools", "Up to 4 broker chart slots", "5 Devices"],
     "entitlements": {"botAccess": True, "modes": ["STRATEGY", "AI", "STRATEGY_AI"], "connectors": ["pocket_option"],
                      "scanners": True, "aiInsights": True, "aiTraining": True, "pretrainedModels": True, "cloudStrategies": True, "community": True,
                      "premiumTools": True, "deviceLimit": 5, "chartLimit": 4}},
]
# Annual variants have stable IDs and the same tools as their monthly tier.
for _monthly, _annual_amount in zip(list(DEFAULT_PLANS), (29995, 99595)):
    _annual = deepcopy(_monthly)
    _annual.update(id=_monthly["id"] + "_yearly", amount=_annual_amount, interval="year",
                   lookup_key="membership_" + _monthly["tier"] + "_yearly", recommended=False)
    DEFAULT_PLANS.append(_annual)
del _monthly, _annual, _annual_amount

# Members who subscribed under the retired plan ids keep working.
LEGACY_PLAN_IDS = {"monthly": "pro", "yearly": "ultimate"}


def find_plan(plans, plan_id):
    direct = next((p for p in plans if p["id"] == plan_id), None)
    if direct: return direct
    plan_id = LEGACY_PLAN_IDS.get(plan_id, plan_id)
    return next((p for p in plans if p["id"] == plan_id), None)


async def get_plans():
    plans = await get_setting("plans")
    return plans or DEFAULT_PLANS


@router.get("/plans")
async def list_plans(response: Response = None):
    if response is not None:response.headers["Cache-Control"]="no-store"
    return await get_plans()


@router.get('/memberships')
async def membership_catalog(response: Response = None):
    if response is not None:response.headers["Cache-Control"]="no-store"
    from kaos.memberships import RATES
    from kaos.affiliate_ledger import DEFAULT_HOLD_DAYS
    plans = [{'id': 'free', 'name': 'Free', 'amount': 0, 'currency': 'usd',
              'interval': None, 'tier': 'free', 'entitlements': dict(FREE_ENTITLEMENTS)}]
    allowed = ('botAccess', 'chartLimit', 'deviceLimit', 'community', 'scanners', 'aiInsights',
               'cloudStrategies', 'premiumTools', 'modes', 'aiTraining', 'pretrainedModels')
    for plan in await get_plans():
        if plan.get('enabled', True) is not True or plan.get('id') == 'free': continue
        tier = plan.get('tier', 'pro')
        plans.append({'id': plan['id'], 'name': plan['name'], 'amount': plan['amount'],
            'currency': plan.get('currency', 'usd'), 'interval': plan.get('interval', 'month'),
            'tier': tier if tier in RATES else 'pro',
            'recommended': plan.get('recommended', tier == 'ultimate' and plan.get('interval', 'month') == 'month') is True,
            'entitlements': {**{key: value for key, value in (plan.get('entitlements') or {}).items() if key in allowed}, 'aiTraining': tier in ('pro','ultimate'), 'pretrainedModels': tier == 'ultimate'}})
    trial_plan=next((p for p in plans if trials.eligible_plan(p)),None)
    affiliate = await get_setting('affiliate_program', {'enabled': True})
    return {'trial':{'days':trials.TRIAL_DAYS,'planId':trial_plan['id'],'amount':trial_plan['amount'],'currency':trial_plan['currency'],'interval':trial_plan['interval']} if trial_plan else None,'plans': plans, 'affiliateRates': {tier: list(rates) for tier, rates in RATES.items()},
            'affiliateEnrollmentEnabled': affiliate.get('enabled') is True, 'payoutsEnabled': False, 'affiliateHoldDays': DEFAULT_HOLD_DAYS,
            'aiExecutionValidated': await get_setting('ai_execution_validated', False) is True,
            **await billing_availability()}


@asynccontextmanager
async def _checkout_lock(user_id,mode):
    key=mode+':'+user_id;claim=uuid4().hex;stamp=time.time()
    try:
        await db.checkout_locks.update_one({'_id':key,'until':{'$lt':stamp}},{'$set':{'until':stamp+300,'owner':claim}},upsert=True)
    except DuplicateKeyError:raise HTTPException(409,'Checkout is already being prepared; retry shortly')
    try:yield
    finally:await db.checkout_locks.update_one({'_id':key,'owner':claim},{'$set':{'until':0}})


async def _price(plan,config):
    fingerprint=hashlib.sha256(json.dumps([config.get('mode','test'),plan['id'],plan['amount'],plan['currency'],plan['interval']],separators=(',',':')).encode()).hexdigest()
    saved=await db.stripe_price_catalog.find_one({'_id':fingerprint})
    if saved:return saved['price_id']
    price=await asyncio.to_thread(stripe.Price.create,api_key=config['key'],idempotency_key='kaos-price-'+fingerprint,
        unit_amount=plan['amount'],currency=plan['currency'],recurring={'interval':plan['interval']},
        metadata={'kaos_plan_id':plan['id']},product_data={'name':f"KAOS {plan['name']} ({plan['interval']})"})
    await db.stripe_price_catalog.update_one({'_id':fingerprint},{'$setOnInsert':{'price_id':price.id,'plan_id':plan['id'],'mode':config.get('mode','test'),'createdAt':now_iso()}},upsert=True)
    return price.id


@router.post('/checkout')
async def checkout(req: CheckoutReq,user:dict=Depends(get_current_user)):
    config=await active_configuration();mode=config.get('mode','test')
    async with _checkout_lock(user['id'],mode):
        # Re-read after acquiring the lease so a just-completed payment is seen.
        fresh=await db.users.find_one({'id':user['id']})
        if not fresh:raise HTTPException(401,'Account unavailable')
        if fresh.get('account_status','active')!='active':raise HTTPException(403,'Account access disabled')
        user=fresh
        if user.get('stripe_subscription_id'):
            current=await _verified_subscription(user['stripe_subscription_id'],user.get('stripe_customer_id'))
            if current.get('status') not in ('canceled','incomplete_expired'):
                raise HTTPException(409,'Manage the existing subscription in billing settings; a second subscription will not be created')
        requested_id=getattr(req,'plan_id',None);lookup=getattr(req,'lookup_key',None)
        plans=await get_plans()
        plan=next((p for p in plans if (p.get('id')==requested_id if requested_id else lookup and p.get('lookup_key')==lookup) and p.get('enabled',True)),None)
        if not plan or plan.get('amount',0)<=0 or (lookup and plan.get('lookup_key')!=lookup):
            raise HTTPException(400,'Paid plan unavailable or selection does not match')
        requested=bool(getattr(req,'start_trial',False))
        if requested and not trials.eligible_plan(plan):raise HTTPException(400,'The free trial is available on Pro monthly only')
        existing=await db.subscriptions.find_one({'userId':user['id'],'state':'initiated'},sort=[('createdAt',-1)])
        if existing:
            if existing.get('stripe_mode',mode)!=mode:raise HTTPException(409,'Existing checkout belongs to another environment; use an isolated test database')
            old=await asyncio.to_thread(stripe.checkout.Session.retrieve,existing['session_id'],api_key=config['key'])
            if identity(old.get('customer'))!=existing.get('stripe_customer_id') or (old.get('metadata') or {}).get('user_id')!=user['id']:
                raise HTTPException(409,'Existing checkout identity requires reconciliation')
            if old.get('status')=='complete':raise HTTPException(409,'The previous payment is being verified; refresh membership status')
            if old.get('status')=='open' and old.get('url'):
                if (bool(existing.get('trial_days'))==requested and existing.get('planId')==plan['id'] and existing.get('amount')==plan['amount']
                        and existing.get('currency')==plan.get('currency','usd') and existing.get('interval')==plan.get('interval','month')):
                    return {'checkout_url':old['url'],'session_id':old['id']}
                await asyncio.to_thread(stripe.checkout.Session.expire,old['id'],api_key=config['key'])
            await db.subscriptions.update_one({'session_id':existing['session_id'],'userId':user['id']},{'$set':{'state':'expired','updatedAt':now_iso()}})
        customer=user.get('stripe_customer_id')
        if not customer:
            key=hashlib.sha256((mode+':'+user['id']).encode()).hexdigest()
            value=await asyncio.to_thread(stripe.Customer.create,api_key=config['key'],idempotency_key='kaos-customer-'+key,email=user['email'],name=user.get('name'),metadata={'user_id':user['id']})
            customer=value.id;await db.users.update_one({'id':user['id']},{'$set':{'stripe_customer_id':customer}})
        price=await _price(plan,config)
        latest=await db.subscriptions.find_one({'userId':user['id']},sort=[('createdAt',-1)])
        previous_id=latest.get('session_id','first') if latest else 'first'
        slot=int(time.time()//1800);key=hashlib.sha256(f"{mode}:{user['id']}:{plan['id']}:{previous_id}:{slot}".encode()).hexdigest()
        trial_fields={}
        if requested:
            trial_key=await trials.reserve(user['email'],config,'user:'+user['id'])
            trial_fields={'trial_key':trial_key,'trial_owner':'user:'+user['id'],'trial_days':trials.TRIAL_DAYS}
        metadata={'user_id':user['id'],'plan_id':plan['id'],'lookup_key':plan['lookup_key'],**({'kaos_trial_days':str(trials.TRIAL_DAYS)} if requested else {})}
        session=await asyncio.to_thread(stripe.checkout.Session.create,api_key=config['key'],idempotency_key='kaos-checkout-'+key,
            **trials.checkout_arguments(requested),
            mode='subscription',customer=customer,line_items=[{'price':price,'quantity':1}],
            success_url=f"{os.environ['FRONTEND_URL'].rstrip('/')}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{os.environ['FRONTEND_URL'].rstrip('/')}/payment/cancel?{urlencode({'plan':plan['id'],**({'trial':'1'} if requested else {})})}",
            metadata=metadata,subscription_data=trials.subscription_arguments({'user_id':user['id'],'plan_id':plan['id'],**({'kaos_trial_days':str(trials.TRIAL_DAYS)} if requested else {})},requested))
        if requested:await trials.attach(trial_key,'user:'+user['id'],session.id)
        await db.subscriptions.update_one({'session_id':session.id},{'$setOnInsert':{**trial_fields,'id':new_id('sub'),'userId':user['id'],'session_id':session.id,'planId':plan['id'],'lookup_key':plan['lookup_key'],'amount':plan['amount'],'currency':plan.get('currency','usd'),'interval':plan.get('interval','month'),'state':'initiated','stripe_customer_id':customer,'stripe_subscription_id':None,'stripe_mode':mode,'createdAt':now_iso(),'updatedAt':now_iso()}},upsert=True)
        return {'checkout_url':session.url,'session_id':session.id}


@router.get("/status/{session_id}")
async def status(session_id: str, user: dict = Depends(get_current_user)):
    rec = await db.subscriptions.find_one({"session_id": session_id, "userId": user["id"]})
    if not rec:
        raise HTTPException(status_code=404, detail="Not found")
    if rec.get("state") not in ("active", "completed"):
        try:
            config = await active_configuration()
            s = await asyncio.to_thread(stripe.checkout.Session.retrieve, session_id, api_key=config["key"])
            if (s.payment_status in ("paid","no_payment_required") and s.status == "complete"
                    and s.get("customer") == rec.get("stripe_customer_id")
                    and s.get("metadata", {}).get("user_id") == user["id"]):
                await _activate(rec["userId"], rec["planId"], s.get("customer"), s.get("subscription"), session_id)
                rec = await db.subscriptions.find_one({"session_id": session_id})
        except stripe.StripeError:
            pass
    return {"session_id": session_id, "state": rec.get("state"),
            "membershipStatus": rec.get("membershipStatus", "PENDING")}


async def _verified_subscription(sub_id, customer):
    config=await active_configuration()
    subscription=await asyncio.to_thread(stripe.Subscription.retrieve,sub_id,api_key=config['key'])
    if identity(subscription.get('customer'))!=customer:
        raise HTTPException(409,'Stripe subscription/customer mismatch')
    return subscription


async def _checkout_invoice(session_id,user_id,plan_id,customer,sub_id):
    config=await active_configuration()
    session=await asyncio.to_thread(stripe.checkout.Session.retrieve,session_id,api_key=config['key'])
    metadata=session.get('metadata') or {}
    owner_matches=metadata.get('user_id')==user_id
    if not owner_matches and metadata.get('guest_purchase_id'):
        guest=await db.guest_purchases.find_one({'_id':metadata['guest_purchase_id'], 'user_id':user_id,
            'session_id':session_id, 'customer_id':customer, 'plan.id':plan_id, 'stripe_mode':config['mode']})
        owner_matches=bool(guest)
    if session.get('payment_status')=='no_payment_required' or (session.get('metadata') or {}).get('kaos_trial_days')==str(trials.TRIAL_DAYS):
        record=await db.subscriptions.find_one({'session_id':session_id,'userId':user_id})
        verified=await _verified_subscription(sub_id,customer)
        await trials.verify(record or {},session,verified,config)
    if (session.get('payment_status') not in ('paid','no_payment_required') or session.get('status')!='complete' or identity(session.get('customer'))!=customer
        or identity(session.get('subscription'))!=sub_id or not owner_matches or metadata.get('plan_id')!=plan_id):
        raise HTTPException(409,'Checkout payment identity does not match the membership')
    invoice_id=identity(session.get('invoice'))
    if not invoice_id:raise HTTPException(503,'Checkout invoice is not ready; retry')
    invoice=await asyncio.to_thread(stripe.Invoice.retrieve,invoice_id,api_key=config['key'])
    if invoice.get('status')!='paid' or identity(invoice.get('customer'))!=customer or subscription_id(invoice)!=sub_id:
        raise HTTPException(409,'Checkout invoice identity does not match the membership')
    return invoice


async def _initial_commission(user,plan,invoice,record):
    # Older versions journaled the initial purchase by checkout ID. Attach its
    # stable invoice alias rather than counting the same payment twice.
    legacy=await db.affiliate_ledger_payments.find_one({'event_id':'checkout:'+record['session_id'],'buyer_id':user['id']})
    if legacy:
        await db.affiliate_ledger_payments.update_one({'event_id':legacy['event_id']},{'$set':{'invoice_id':invoice['id']}})
        return
    if invoice.get('amount_paid',0)>0:
        from routes_affiliate import record_commission
        await record_commission(user,plan,'purchase',event_id='invoice:'+invoice['id'],amount_cents=invoice['amount_paid'])


async def _activate(user_id, plan_id, customer, subscription, session_id):
    record=await db.subscriptions.find_one({'session_id':session_id,'userId':user_id,'planId':plan_id})
    plan=find_plan(await get_plans(),plan_id)
    if not record or not plan:raise HTTPException(503,'Checkout relationship not ready; retry reconciliation')
    verified=await _verified_subscription(subscription,customer)
    if verified.get('status') not in ('active','trialing'):
        raise HTTPException(409,'Subscription is not active')
    end=period_end(verified)
    if end<=now().timestamp():raise HTTPException(409,'Subscription period has already ended')
    invoice=await _checkout_invoice(session_id,user_id,plan_id,customer,subscription)
    is_trial=verified.get('status')=='trialing'
    if is_trial:
        end=min(end,int(verified.get('trial_end') or 0))
        if end<=now().timestamp():raise HTTPException(409,'Trial has expired')
        if not record.get('trial_key'):raise HTTPException(409,'Trial reservation is missing')
        await trials.consume(record,session_id)
    membership_status='TRIAL' if is_trial else 'ACTIVE'
    expires=iso(end)
    await db.subscriptions.update_one({'session_id':session_id}, {'$set':{
        'state':'active','membershipStatus':membership_status,'stripe_subscription_id':subscription,
        'period_end':end,'invoice_id':invoice['id'],'updatedAt':now_iso()}})
    await db.users.update_one({'id':user_id},{'$set':{
        'membership_status':membership_status,'membership_plan':plan_id,'membership_expires_at':expires,
        'stripe_paid_through':end,'stripe_subscription_id':subscription,'stripe_customer_id':customer,
        'cancel_at_period_end':bool(verified.get('cancel_at_period_end')),'onboarding_step':7,'updated_at':now_iso()}})
    if is_trial:await db.users.update_one({'id':user_id},{'$set':{'pro_trial_ends_at':expires}})
    # Retrying the same checkout uses the same ledger identity, including after a partial failure.
    customer_user=await db.users.find_one({'id':user_id})
    if not is_trial:await _initial_commission(customer_user,plan,invoice,record)


async def _paid_invoice(invoice):
    customer=identity(invoice.get('customer'));sub_id=subscription_id(invoice)
    if not customer or not sub_id:return
    user=await db.users.find_one({'stripe_customer_id':customer})
    if not user:raise HTTPException(503,'Invoice customer relationship not ready; retry')
    record=await db.subscriptions.find_one({'stripe_subscription_id':sub_id,'userId':user['id']})
    if not record:raise HTTPException(503,'Invoice subscription relationship not ready; retry')
    plan=find_plan(await get_plans(),record.get('planId'))
    if not plan:raise HTTPException(503,'Invoice membership plan needs reconciliation')
    verified=await _verified_subscription(sub_id,customer)
    if verified.get('status')=='trialing':
        if invoice.get('amount_paid',0)>0:raise HTTPException(503,'Paid subscription transition is still processing; retry')
        return
    end=invoice_period_end(invoice,sub_id)
    if end is None:end=period_end(verified)
    if user.get('stripe_subscription_id')==sub_id and verified.get('status') in ('past_due','unpaid') and end>now().timestamp():
        raise HTTPException(503,'Stripe subscription status is still reconciling; retry')
    # An old invoice cannot extend or reactivate a different/currently expired subscription.
    if verified.get('status') in ('active','trialing') and user.get('stripe_subscription_id')==sub_id and end>now().timestamp() and end>=int(user.get('stripe_paid_through') or 0):
        await db.users.update_one({'id':user['id'],'stripe_subscription_id':sub_id},{'$set':{
            'membership_status':'ACTIVE','membership_plan':plan['id'],'updated_at':now_iso()},
            '$max':{'stripe_paid_through':end,'membership_expires_at':iso(end)}})
        await db.subscriptions.update_one({'stripe_subscription_id':sub_id,'userId':user['id']},{'$max':{'period_end':end},'$set':{'membershipStatus':'ACTIVE','updatedAt':now_iso()}})
    if invoice.get('billing_reason')=='subscription_create':
        await _initial_commission(user,plan,invoice,record)
    if invoice.get('billing_reason')=='subscription_cycle' and invoice.get('amount_paid',0)>0:
        from routes_affiliate import record_commission
        await record_commission(user,plan,'renewal',event_id=f"invoice:{invoice['id']}",amount_cents=invoice['amount_paid'])


@router.post("/portal")
async def billing_portal(req: CheckoutReq, user: dict = Depends(get_current_user)):
    config = await active_configuration()
    if not user.get("stripe_customer_id"):
        raise HTTPException(status_code=400, detail="No billing account")
    session = await asyncio.to_thread(stripe.billing_portal.Session.create,api_key=config["key"], customer=user["stripe_customer_id"],
                                                    return_url=f"{os.environ['FRONTEND_URL'].rstrip('/')}/dashboard/subscription")
    return {"url": session.url}


@router.post("/cancel")
async def cancel(user: dict = Depends(get_current_user)):
    config = await active_configuration()
    sub_id = user.get("stripe_subscription_id")
    if sub_id:
        try:
            await asyncio.to_thread(stripe.Subscription.modify,sub_id, cancel_at_period_end=True, api_key=config["key"])
        except stripe.StripeError as exc:
            raise HTTPException(status_code=502, detail="Stripe cancellation failed") from exc
    await db.users.update_one({"id": user["id"]}, {"$set": {"cancel_at_period_end": bool(sub_id), "updated_at": now_iso()}})
    return {"canceled": True}


# Stripe webhook (authoritative, idempotent, signature-verified)
webhook_router = APIRouter(tags=["billing"])


@webhook_router.post("/api/stripe/webhook")
async def stripe_webhook(request: Request):
    config = await active_configuration()
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(payload, sig, config["secret"])
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid signature")
    if config.get('mode') in ('test','live') and event.get('livemode') is not (config['mode']=='live'):
        raise HTTPException(400,'Stripe event environment does not match billing configuration')
    # Record receipt separately from successful processing so a failed event
    # remains retryable. Unique event_id index is created in db.ensure_indexes.
    from pymongo.errors import DuplicateKeyError
    try:
        await db.webhook_events.insert_one({"_id":event["id"], "event_id": event["id"], "type": event["type"],
                                            "state": "received", "livemode": event.get("livemode"), "createdAt": now_iso()})
    except Exception as exc:
        if not (isinstance(exc, DuplicateKeyError) or
                (type(exc).__name__ == "DuplicateKeyError" and
                 type(exc).__module__ == "pymongo.errors")):
            raise
        existing = await db.webhook_events.find_one({"event_id": event["id"]})
        if existing and existing.get("state") == "completed":
            return {"status": "duplicate"}
        # A retry must be allowed to finish a previously interrupted event.
        # Lease ownership atomically; do not concurrently run financial effects.
        from datetime import datetime, timezone, timedelta
        from uuid import uuid4
        claim = str(uuid4())
        now_at = datetime.now(timezone.utc)
        lease = await db.webhook_events.update_one(
            {"event_id": event["id"], "state": {"$in": ["received", "processing"]},
             "$or": [{"lease_until": {"$lt": now_at}}, {"lease_until": {"$exists": False}}]},
            {"$set": {"state": "processing", "claim": claim,
                       "lease_until": now_at + timedelta(minutes=5)}})
        if lease.modified_count != 1:
            raise HTTPException(status_code=503, detail="Webhook already processing; retry later")
    else:
        from datetime import datetime, timezone, timedelta
        from uuid import uuid4
        claim = str(uuid4())
        claimed = await db.webhook_events.update_one(
            {"event_id": event["id"], "state": "received"},
            {"$set": {"state": "processing", "claim": claim,
                       "lease_until": datetime.now(timezone.utc) + timedelta(minutes=5)}})
        if claimed.modified_count != 1:
            raise HTTPException(status_code=503, detail="Unable to claim webhook event; retry later")
    obj = event["data"]["object"]
    t = event["type"]
    if t in ("checkout.session.completed", "checkout.session.async_payment_succeeded"):
        meta = obj.get("metadata", {})
        confirmed = obj.get('payment_status')=='paid' or (obj.get('payment_status')=='no_payment_required' and meta.get('kaos_trial_days')==str(trials.TRIAL_DAYS))
        # A completed Checkout can still be unpaid for delayed payment methods.
        # Only the paid transition may grant membership/affiliate commission.
        if meta.get('guest_purchase_id') and confirmed and obj.get('status')=='complete':
            from guest_checkout import from_webhook
            await from_webhook(obj['id'])
        elif meta.get("user_id") and confirmed and obj.get("status") == "complete":
            await _activate(meta["user_id"], meta.get("plan_id"), obj.get("customer"), obj.get("subscription"), obj["id"])
    elif t=='customer.subscription.trial_will_end':
        await trials.reminder(obj,config)
    elif t in ('invoice.payment_failed','customer.subscription.deleted'):
        customer=identity(obj.get('customer'))
        sub_id=subscription_id(obj) if t=='invoice.payment_failed' else obj.get('id')
        apply_status=True
        if t=='invoice.payment_failed' and customer and sub_id:
            verified=await _verified_subscription(sub_id,customer)
            apply_status=verified.get('status') in ('past_due','unpaid','incomplete')
        if customer and sub_id and apply_status:
            # Delayed events for a replaced subscription cannot revoke the current one.
            await db.users.update_one({'stripe_customer_id':customer,'stripe_subscription_id':sub_id},{'$set':{
                'membership_status':'PAST_DUE' if t=='invoice.payment_failed' else 'EXPIRED','updated_at':now_iso()}})
        # Cancellation stops future access/renewals, not an already-earned commission.
        # Only an actual refund or dispute reverses the payment ledger.
    elif t == 'invoice.paid':
        from guest_checkout import guest_invoice
        if not await guest_invoice(obj): await _paid_invoice(obj)
    elif t=='charge.dispute.created':
        charge_id=identity(obj.get('charge'))
        if not charge_id:raise HTTPException(503,'Dispute charge identity unavailable')
        charge=await asyncio.to_thread(stripe.Charge.retrieve,charge_id,api_key=config['key'])
        if charge.get('id')!=charge_id:raise HTTPException(409,'Dispute charge identity mismatch')
        await _reverse_for_charge({'charge':charge_id,'amount':obj.get('amount'),
            'customer':identity(charge.get('customer')),'invoice':identity(charge.get('invoice')),'dispute_id':obj.get('id')},'chargeback')
    elif t=='charge.refunded':
        await _reverse_for_charge(obj,'refund')
    completed = await db.webhook_events.update_one(
        {"event_id": event["id"], "claim": claim, "state": "processing"},
        {"$set": {"state": "completed", "completedAt": now_iso()},
         "$unset": {"lease_until": "", "claim": ""}})
    if completed.modified_count != 1:
        raise HTTPException(status_code=503, detail="Webhook completion not recorded; reconciliation required")
    return {"status": "ok"}


async def _reverse_for_charge(obj, reason):
    """Offset affiliate commissions for a refunded or disputed charge (incremental for partial refunds)."""
    charge_id = obj.get("charge") if reason == "chargeback" else obj.get("id")
    if not isinstance(charge_id, str) or not charge_id.strip():
        raise RuntimeError("Stripe reversal missing charge identity; reconciliation required")
    customer_id = obj.get("customer")
    if not isinstance(customer_id, str) or not customer_id.strip():
        raise RuntimeError("Stripe reversal missing customer identity; reconciliation required")
    u = await db.users.find_one({"stripe_customer_id": customer_id})
    if not u:
        raise RuntimeError("Stripe reversal customer not found; reconciliation required")
    invoice_id = obj.get("invoice")
    if not invoice_id:
        # Never reverse an arbitrary recent payment when Stripe supplied no
        # stable invoice identity. Queue for operator reconciliation instead.
        raise RuntimeError("Stripe reversal missing invoice identity; reconciliation required")
    pay = await db.affiliate_ledger_payments.find_one({"event_id": f"invoice:{invoice_id}"})
    if not pay:
        pay=await db.affiliate_ledger_payments.find_one({'invoice_id':invoice_id,'buyer_id':u['id']})
    if not pay:
        # A checkout may have been paid before the invoice journal exists.
        # Do not guess which payment to reverse by sorting a buyer's history.
        raise RuntimeError("Stripe reversal payment journal not found; reconciliation required")
    if pay.get("buyer_id") != u["id"]:
        raise RuntimeError("Stripe reversal customer does not match ledger buyer")
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
                                 reversal_id=(f"refund:{charge_id}:through:{int(obj.get('amount_refunded') or 0)}" if reason=="refund" else f"chargeback:{obj.get('dispute_id') or charge_id}:amount:{int(obj.get('amount') or 0)}"))
    except Exception:
        logger.exception("affiliate reversal failed for %s; webhook will retry", charge_id)
        raise
