"""Repeated checkout clicks must reuse or wait, not multiply billing sessions."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock,Mock
import pytest
from fastapi import HTTPException
import routes_billing as billing


def setup(monkeypatch,status='open'):
    user={'id':'buyer','email':'buyer@example.com','stripe_customer_id':'cus-test'}
    record={'session_id':'cs-test','stripe_customer_id':'cus-test','planId':'pro','stripe_mode':'test','amount':2995,'currency':'usd','interval':'month'}
    db=SimpleNamespace(users=SimpleNamespace(find_one=AsyncMock(return_value=user)),checkout_locks=SimpleNamespace(update_one=AsyncMock()),subscriptions=SimpleNamespace(find_one=AsyncMock(return_value=record),update_one=AsyncMock()))
    monkeypatch.setattr(billing,'db',db);monkeypatch.setattr(billing,'active_configuration',AsyncMock(return_value={'key':'fixture','mode':'test'}));monkeypatch.setattr(billing,'get_plans',AsyncMock(return_value=billing.DEFAULT_PLANS))
    monkeypatch.setattr(billing.stripe.checkout.Session,'retrieve',Mock(return_value={'id':'cs-test','customer':'cus-test','status':status,'metadata':{'user_id':'buyer'},'url':'https://checkout.stripe.com/fixture'}))
    create=Mock();monkeypatch.setattr(billing.stripe.checkout.Session,'create',create)
    return db,user,create


def test_repeated_click_reuses_existing_open_checkout(monkeypatch):
    db,user,create=setup(monkeypatch)
    result=asyncio.run(billing.checkout(SimpleNamespace(lookup_key='membership_pro_monthly'),user))
    assert result=={'checkout_url':'https://checkout.stripe.com/fixture','session_id':'cs-test'}
    create.assert_not_called();db.subscriptions.update_one.assert_not_awaited()
    assert db.checkout_locks.update_one.await_count==2
    assert 'owner' in db.checkout_locks.update_one.await_args.args[0]


def test_paid_checkout_waits_for_reconciliation_instead_of_second_charge(monkeypatch):
    _,user,create=setup(monkeypatch,'complete')
    with pytest.raises(HTTPException) as failure:asyncio.run(billing.checkout(SimpleNamespace(lookup_key='membership_pro_monthly'),user))
    assert failure.value.status_code==409;create.assert_not_called()


def test_another_request_cannot_release_the_active_checkout_lease(monkeypatch):
    db,user,create=setup(monkeypatch)
    db.checkout_locks.update_one.side_effect=billing.DuplicateKeyError('busy')
    with pytest.raises(HTTPException) as failure:asyncio.run(billing.checkout(SimpleNamespace(lookup_key='membership_pro_monthly'),user))
    assert failure.value.status_code==409
    assert db.checkout_locks.update_one.await_count==1
    create.assert_not_called()


def test_cached_price_is_reused_without_creating_another_product(monkeypatch):
    db=SimpleNamespace(stripe_price_catalog=SimpleNamespace(find_one=AsyncMock(return_value={'price_id':'price-known'})))
    monkeypatch.setattr(billing,'db',db);create=Mock();monkeypatch.setattr(billing.stripe.Price,'create',create)
    assert asyncio.run(billing._price(billing.DEFAULT_PLANS[0],{'key':'fixture','mode':'test'}))=='price-known'
    create.assert_not_called()


def test_an_open_checkout_with_old_price_is_replaced_with_current_selected_terms(monkeypatch):
    db,user,create=setup(monkeypatch)
    record=db.subscriptions.find_one.return_value
    record['amount']=2900
    expire=Mock();monkeypatch.setattr(billing.stripe.checkout.Session,'expire',expire)
    monkeypatch.setattr(billing,'_price',AsyncMock(return_value='price_current'))
    create.return_value=SimpleNamespace(id='cs_current',url='https://checkout.stripe.com/c/pay/cs_current')
    monkeypatch.setenv('FRONTEND_URL','https://tradingwithkaos.com')
    result=asyncio.run(billing.checkout(SimpleNamespace(plan_id='pro'),user))
    expire.assert_called_once_with('cs-test',api_key='fixture')
    assert result['session_id']=='cs_current'
    assert create.call_args.kwargs['line_items']==[{'price':'price_current','quantity':1}]
