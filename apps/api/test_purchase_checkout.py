"""Homepage plan IDs select server prices. No actual Stripe account is contacted."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock,Mock
import pytest
from fastapi import HTTPException
from models import CheckoutReq
import routes_billing as billing


@pytest.fixture
def setup(monkeypatch):
    user={'id':'buyer','email':'buyer@example.com','stripe_customer_id':'cus_fixture'}
    database=SimpleNamespace(users=SimpleNamespace(find_one=AsyncMock(return_value=user)),
        checkout_locks=SimpleNamespace(update_one=AsyncMock()),
        subscriptions=SimpleNamespace(find_one=AsyncMock(return_value=None),update_one=AsyncMock()))
    monkeypatch.setattr(billing,'db',database)
    monkeypatch.setattr(billing,'active_configuration',AsyncMock(return_value={'key':'fixture','mode':'test'}))
    monkeypatch.setattr(billing,'get_plans',AsyncMock(return_value=billing.DEFAULT_PLANS))
    price=AsyncMock(return_value='price_fixture');monkeypatch.setattr(billing,'_price',price)
    create=Mock(return_value=SimpleNamespace(id='cs_fixture',url='https://checkout.stripe.com/c/pay/cs_fixture'))
    monkeypatch.setattr(billing.stripe.checkout.Session,'create',create)
    monkeypatch.setenv('FRONTEND_URL','https://tradingwithkaos.com')
    return SimpleNamespace(user=user,db=database,price=price,create=create)


@pytest.mark.parametrize('plan_id,amount,interval',[('pro',2995,'month'),('pro_yearly',29995,'year'),('ultimate',9995,'month'),('ultimate_yearly',99595,'year')])
def test_public_plan_id_drives_server_price_and_retained_cancel_selection(setup,plan_id,amount,interval):
    result=asyncio.run(billing.checkout(CheckoutReq(plan_id=plan_id,origin_url='https://untrusted.example'),setup.user))
    assert result['checkout_url'].startswith('https://checkout.stripe.com/')
    plan=setup.price.call_args.args[0]
    assert plan['id']==plan_id and plan['amount']==amount and plan['interval']==interval
    created=setup.create.call_args.kwargs
    assert created['metadata']['plan_id']==plan_id
    assert created['cancel_url']=='https://tradingwithkaos.com/payment/cancel?plan='+plan_id
    assert created['success_url'].startswith('https://tradingwithkaos.com/payment/success?')
    # Creating a session records a pending purchase; it never activates membership.
    assert setup.db.subscriptions.update_one.call_args.args[1]['$setOnInsert']['state']=='initiated'


@pytest.mark.parametrize('body',[{'plan_id':'free'},{'plan_id':'nonexistent'},
    {'plan_id':'pro','lookup_key':'membership_ultimate_monthly'},{}])
def test_invalid_or_conflicting_selection_never_creates_a_checkout(setup,body):
    with pytest.raises(HTTPException):asyncio.run(billing.checkout(CheckoutReq(**body),setup.user))
    setup.price.assert_not_awaited();setup.create.assert_not_called()


def test_exact_legacy_saved_plan_precedes_historical_aliases():
    legacy={'id':'yearly','amount':27900,'tier':'pro'}
    assert billing.find_plan([legacy,*billing.DEFAULT_PLANS],'yearly') is legacy
    assert billing.find_plan(billing.DEFAULT_PLANS,'yearly')['id']=='ultimate'


def test_admin_payment_status_tracks_checkout_runtime_without_enabling_payouts(monkeypatch):
    import stripe_runtime
    import routes_commerce_admin as admin
    monkeypatch.setattr(stripe_runtime,'availability',AsyncMock(return_value={'checkoutEnabled':True,'mode':'live'}))
    monkeypatch.setattr(admin.providers,'public_provider',AsyncMock(side_effect=lambda provider:{'id':provider,'paymentsLive':False,'payoutsLive':False}))
    monkeypatch.setattr(admin.providers,'vault_ready',lambda:True)
    result=asyncio.run(admin.get_providers({'id':'owner'}))
    methods={p['id']:p for p in result['providers']}
    assert methods['stripe']['paymentsLive'] is True
    assert not any(p['payoutsLive'] for p in methods.values())
    assert 'enabled in live mode' in result['activationNote']
