"""Real subscription periods, safe lifecycle replay, and earned commissions."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
from datetime import datetime,timezone,timedelta
import pytest
from fastapi import HTTPException
import billing_periods as periods
import routes_billing as billing
import routes_affiliate as affiliate


def end(days=35):return int((datetime.now(timezone.utc)+timedelta(days=days)).timestamp())


def fixture(monkeypatch,*,sub='sub-current',paid=None,verified_status='active',record=True):
    expiry=end();user={'id':'buyer','stripe_customer_id':'cus-test','stripe_subscription_id':sub,'membership_status':'PAST_DUE','membership_plan':'ultimate','stripe_paid_through':paid or 0}
    users=SimpleNamespace(find_one=AsyncMock(return_value=user),update_one=AsyncMock())
    subscriptions=SimpleNamespace(find_one=AsyncMock(return_value={'userId':'buyer','planId':'pro_yearly','session_id':'cs-test'} if record else None),update_one=AsyncMock())
    monkeypatch.setattr(billing,'db',SimpleNamespace(users=users,subscriptions=subscriptions,affiliate_ledger_payments=SimpleNamespace(find_one=AsyncMock(return_value=None),update_one=AsyncMock())))
    monkeypatch.setattr(billing,'get_plans',AsyncMock(return_value=billing.DEFAULT_PLANS))
    monkeypatch.setattr(billing,'_verified_subscription',AsyncMock(return_value={'customer':'cus-test','status':verified_status,'current_period_end':expiry}))
    monkeypatch.setattr(billing,'_checkout_invoice',AsyncMock(return_value={'id':'in-initial','amount_paid':29995,'customer':'cus-test','subscription':'sub-current'}))
    ledger=AsyncMock();monkeypatch.setattr(affiliate,'record_commission',ledger)
    invoice={'id':'in-test','customer':'cus-test','subscription':'sub-current','billing_reason':'subscription_cycle','amount_paid':29995,'lines':{'data':[{'type':'subscription','subscription':'sub-current','period':{'end':expiry}}]}}
    return users,subscriptions,ledger,invoice,expiry


def test_period_helpers_support_current_and_legacy_stripe_shapes():
    value=end()
    assert periods.period_end({'items':{'data':[{'current_period_end':value}]}})==value
    assert periods.period_end({'current_period_end':value})==value
    assert periods.subscription_id({'parent':{'subscription_details':{'subscription':{'id':'sub-x'}}}})=='sub-x'
    assert periods.invoice_period_end({'lines':{'data':[{'parent':{'subscription_item_details':{'subscription':'sub-x'}},'period':{'end':value}}]}},'sub-x')==value
    with pytest.raises(HTTPException):periods.period_end({'items':{'data':[]}})


def test_checkout_uses_stripe_period_not_a_guessed_month_or_year(monkeypatch):
    users,subscriptions,ledger,_,expiry=fixture(monkeypatch)
    asyncio.run(billing._activate('buyer','pro_yearly','cus-test','sub-current','cs-test'))
    update=users.update_one.await_args.args[1]['$set']
    assert update['membership_expires_at']==periods.iso(expiry)
    assert update['stripe_paid_through']==expiry and update['membership_plan']=='pro_yearly'
    assert ledger.await_args.kwargs['event_id']=='invoice:in-initial'
    assert ledger.await_args.kwargs['amount_cents']==29995


def test_paid_renewal_extends_expiry_and_uses_subscription_plan(monkeypatch):
    users,subscriptions,ledger,invoice,expiry=fixture(monkeypatch)
    asyncio.run(billing._paid_invoice(invoice))
    update=users.update_one.await_args.args[1]
    assert update['$max']['stripe_paid_through']==expiry
    assert update['$max']['membership_expires_at']==periods.iso(expiry)
    assert update['$set']['membership_status']=='ACTIVE'
    assert ledger.await_args.args[1]['id']=='pro_yearly'
    assert ledger.await_args.kwargs=={'event_id':'invoice:in-test','amount_cents':29995}


@pytest.mark.parametrize('kind',['older_period','different_subscription','canceled'])
def test_old_or_canceled_payment_cannot_reactivate_membership(monkeypatch,kind):
    users,_,ledger,invoice,expiry=fixture(monkeypatch,sub='sub-new' if kind=='different_subscription' else 'sub-current',paid=end(50) if kind=='older_period' else None,verified_status='canceled' if kind=='canceled' else 'active')
    asyncio.run(billing._paid_invoice(invoice))
    users.update_one.assert_not_awaited()
    ledger.assert_awaited_once()  # A real historical paid renewal still uses its own payment identity.


def test_invoice_before_checkout_mapping_is_retryable_not_lost(monkeypatch):
    users,_,ledger,invoice,_=fixture(monkeypatch,record=False)
    with pytest.raises(HTTPException) as failure:asyncio.run(billing._paid_invoice(invoice))
    assert failure.value.status_code==503
    users.update_one.assert_not_awaited();ledger.assert_not_awaited()


def test_paid_recovery_waits_for_current_stripe_status(monkeypatch):
    users,_,ledger,invoice,_=fixture(monkeypatch,verified_status='past_due')
    with pytest.raises(HTTPException) as failure:asyncio.run(billing._paid_invoice(invoice))
    assert failure.value.status_code==503
    users.update_one.assert_not_awaited();ledger.assert_not_awaited()


def webhook(monkeypatch,kind,obj,mode='test',live=False):
    events=SimpleNamespace(insert_one=AsyncMock(),update_one=AsyncMock(return_value=SimpleNamespace(modified_count=1)))
    users=SimpleNamespace(update_one=AsyncMock())
    monkeypatch.setattr(billing,'db',SimpleNamespace(webhook_events=events,users=users))
    monkeypatch.setattr(billing,'active_configuration',AsyncMock(return_value={'key':'fixture','secret':'fixture','mode':mode}))
    monkeypatch.setattr(billing.stripe.Webhook,'construct_event',lambda *args:{'id':'evt-x','type':kind,'livemode':live,'data':{'object':obj}})
    request=SimpleNamespace(body=AsyncMock(return_value=b'fixture'),headers={'stripe-signature':'fixture'})
    return request,users,events


def test_cancellation_does_not_reverse_an_earned_payment(monkeypatch):
    reverse=AsyncMock();monkeypatch.setattr(affiliate,'reverse_commission',reverse)
    request,users,_=webhook(monkeypatch,'customer.subscription.deleted',{'id':'sub-old','customer':'cus-test'})
    assert asyncio.run(billing.stripe_webhook(request))=={'status':'ok'}
    assert users.update_one.await_args.args[0]=={'stripe_customer_id':'cus-test','stripe_subscription_id':'sub-old'}
    reverse.assert_not_awaited()


def test_stale_failure_does_not_override_current_active_stripe_status(monkeypatch):
    request,users,_=webhook(monkeypatch,'invoice.payment_failed',{'subscription':'sub-current','customer':'cus-test'})
    monkeypatch.setattr(billing,'_verified_subscription',AsyncMock(return_value={'status':'active'}))
    asyncio.run(billing.stripe_webhook(request));users.update_one.assert_not_awaited()


def test_wrong_environment_rejected_before_any_financial_effect(monkeypatch):
    request,users,events=webhook(monkeypatch,'invoice.paid',{},mode='live',live=False)
    with pytest.raises(HTTPException) as failure:asyncio.run(billing.stripe_webhook(request))
    assert failure.value.status_code==400
    users.update_one.assert_not_awaited();events.insert_one.assert_not_awaited()


def test_legacy_checkout_payment_gets_invoice_alias_without_double_credit(monkeypatch):
    users,_,ledger,invoice,_=fixture(monkeypatch)
    payments=billing.db.affiliate_ledger_payments
    payments.find_one.return_value={'event_id':'checkout:cs-test','buyer_id':'buyer'}
    asyncio.run(billing._initial_commission({'id':'buyer'},billing.DEFAULT_PLANS[0],{'id':'in-test','amount_paid':2995},{'session_id':'cs-test'}))
    ledger.assert_not_awaited()
    assert payments.update_one.await_args.args[1]['$set']['invoice_id']=='in-test'


def test_dispute_fetches_exact_charge_before_reversal(monkeypatch):
    request,_,_=webhook(monkeypatch,'charge.dispute.created',{'id':'dp-test','charge':'ch-test','amount':1000})
    monkeypatch.setattr(billing.stripe.Charge,'retrieve',lambda *a,**k:{'id':'ch-test','customer':'cus-test','invoice':'in-test'})
    reverse=AsyncMock();monkeypatch.setattr(billing,'_reverse_for_charge',reverse)
    asyncio.run(billing.stripe_webhook(request))
    assert reverse.await_args.args==({'charge':'ch-test','amount':1000,'customer':'cus-test','invoice':'in-test','dispute_id':'dp-test'},'chargeback')


def test_existing_subscription_cannot_be_charged_as_a_second_checkout(monkeypatch):
    monkeypatch.setattr(billing,'active_configuration',AsyncMock(return_value={'key':'fixture'}))
    monkeypatch.setattr(billing,'_verified_subscription',AsyncMock(return_value={'status':'active'}))
    monkeypatch.setattr(billing,'db',SimpleNamespace(checkout_locks=SimpleNamespace(update_one=AsyncMock()),users=SimpleNamespace(find_one=AsyncMock(return_value={'id':'buyer','stripe_customer_id':'cus-test','stripe_subscription_id':'sub-current'}))))
    create=AsyncMock();monkeypatch.setattr(billing.stripe.Customer,'create',create)
    with pytest.raises(HTTPException) as failure:
        asyncio.run(billing.checkout(SimpleNamespace(lookup_key='membership_ultimate_monthly'),{'id':'buyer','stripe_customer_id':'cus-test','stripe_subscription_id':'sub-current'}))
    assert failure.value.status_code==409
    create.assert_not_called()


def test_equal_partial_refunds_have_distinct_cumulative_reversal_ids(monkeypatch):
    from decimal import Decimal
    payment={'event_id':'invoice:in-test','buyer_id':'buyer','amount':'20','reversed_amount':'0'}
    monkeypatch.setattr(billing,'db',SimpleNamespace(users=SimpleNamespace(find_one=AsyncMock(return_value={'id':'buyer'})),affiliate_ledger_payments=SimpleNamespace(find_one=AsyncMock(return_value=payment))))
    calls=[]
    async def reverse(*args,**kwargs):
        calls.append(kwargs);payment['reversed_amount']=str(Decimal(payment['reversed_amount'])+Decimal(kwargs['amount_cents'])/100)
    monkeypatch.setattr(affiliate,'reverse_commission',reverse)
    async def run():
        for amount in (500,1000,1000):await billing._reverse_for_charge({'id':'ch-test','invoice':'in-test','customer':'cus-test','amount_refunded':amount},'refund')
    asyncio.run(run())
    assert [c['amount_cents'] for c in calls]==[500,500]
    assert calls[0]['reversal_id']!=calls[1]['reversal_id']
    assert payment['reversed_amount']=='10'
