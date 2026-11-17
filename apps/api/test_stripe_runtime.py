"""Saved settings must be usable without accidentally enabling charges."""
import asyncio
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
import stripe_runtime as runtime


def setup(monkeypatch, mode='sandbox', key='sk_test_fixture', secret='whsec_fixture'):
    monkeypatch.delenv('KAOS_STRIPE_CHECKOUT_ENABLED', raising=False)
    monkeypatch.delenv('KAOS_LOGIN_VALIDATION_MODE', raising=False)
    monkeypatch.setattr(runtime.providers, 'document', AsyncMock(return_value={'mode':mode,'paymentsSelected':True}))
    monkeypatch.setattr(runtime.providers, 'credentials', AsyncMock(return_value={'secret_key':key,'webhook_secret':secret}))


def test_saved_vault_credentials_are_ready_but_not_enabled(monkeypatch):
    setup(monkeypatch)
    result=asyncio.run(runtime.availability())
    assert result['configurationReady'] is True and result['checkoutEnabled'] is False
    assert 'sk_test_fixture' not in str(result) and 'whsec_fixture' not in str(result)
    with pytest.raises(HTTPException):asyncio.run(runtime.active_configuration())


@pytest.mark.parametrize('mode,key,secret',[('sandbox','sk_live_fixture','whsec_fixture'),('live','sk_test_fixture','whsec_fixture'),('sandbox','sk_test_fixture','')])
def test_mismatched_or_incomplete_setup_cannot_launch(monkeypatch,mode,key,secret):
    setup(monkeypatch,mode,key,secret)
    monkeypatch.setenv('KAOS_STRIPE_CHECKOUT_ENABLED','true')
    assert asyncio.run(runtime.availability())['checkoutEnabled'] is False


def test_host_validation_policy_still_blocks_saved_credentials(monkeypatch):
    setup(monkeypatch)
    monkeypatch.setenv('KAOS_STRIPE_CHECKOUT_ENABLED','true')
    monkeypatch.setenv('KAOS_LOGIN_VALIDATION_MODE','true')
    result=asyncio.run(runtime.availability())
    assert result['checkoutEnabled'] is False and 'blocks' in result['note']


def test_per_request_credentials_require_explicit_activation(monkeypatch):
    setup(monkeypatch)
    monkeypatch.setenv('KAOS_STRIPE_CHECKOUT_ENABLED','true')
    assert asyncio.run(runtime.active_configuration())['key']=='sk_test_fixture'


def test_checkout_passes_saved_key_to_each_stripe_call(monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import Mock
    import routes_billing as billing
    monkeypatch.setattr(billing,'active_configuration',AsyncMock(return_value={'key':'sk_test_vault_fixture'}))
    monkeypatch.setattr(billing,'get_plans',AsyncMock(return_value=billing.DEFAULT_PLANS))
    customer=Mock(return_value=SimpleNamespace(id='cus_fixture'))
    price=Mock(return_value=SimpleNamespace(id='price_fixture'))
    session=Mock(return_value=SimpleNamespace(id='cs_fixture',url='https://checkout.stripe.com/fixture'))
    monkeypatch.setattr(billing.stripe.Customer,'create',customer)
    monkeypatch.setattr(billing.stripe.Price,'create',price)
    monkeypatch.setattr(billing.stripe.checkout.Session,'create',session)
    monkeypatch.setattr(billing,'db',SimpleNamespace(checkout_locks=SimpleNamespace(update_one=AsyncMock()),stripe_price_catalog=SimpleNamespace(find_one=AsyncMock(return_value=None),update_one=AsyncMock()),users=SimpleNamespace(update_one=AsyncMock(),find_one=AsyncMock(return_value={'id':'fixture','email':'member@example.com'})),subscriptions=SimpleNamespace(find_one=AsyncMock(return_value=None),update_one=AsyncMock())))
    monkeypatch.setenv('FRONTEND_URL','https://example.com')
    result=asyncio.run(billing.checkout(SimpleNamespace(lookup_key='membership_pro_monthly'),{'id':'fixture','email':'member@example.com'}))
    assert result['checkout_url']=='https://checkout.stripe.com/fixture'
    for call in (customer,price,session):assert call.call_args.kwargs['api_key']=='sk_test_vault_fixture'
    assert price.call_args.kwargs['unit_amount']==2995


def test_disabled_checkout_never_contacts_stripe(monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import Mock
    import routes_billing as billing
    setup(monkeypatch)
    customer=Mock()
    monkeypatch.setattr(billing.stripe.Customer,'create',customer)
    with pytest.raises(HTTPException):
        asyncio.run(billing.checkout(SimpleNamespace(lookup_key='membership_pro_monthly'),{'id':'fixture'}))
    customer.assert_not_called()
