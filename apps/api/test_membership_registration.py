import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException, Response
from models import RegisterReq
import routes_auth as auth
import routes_billing as billing


@pytest.fixture
def registration(monkeypatch):
    users=SimpleNamespace(find_one=AsyncMock(return_value=None),insert_one=AsyncMock(),update_one=AsyncMock())
    monkeypatch.setattr(auth,'db',SimpleNamespace(users=users))
    monkeypatch.setattr(billing,'get_plans',AsyncMock(return_value=billing.DEFAULT_PLANS))
    monkeypatch.setenv('JWT_SECRET','fixture-registration-secret-only')
    return users


@pytest.mark.parametrize('plan_id',['free','pro','ultimate',None])
def test_signup_remembers_choice_and_referral_without_granting_paid_access(registration,plan_id):
    result=asyncio.run(auth.register(RegisterReq(email='new@example.com',name='New member',password='fixture-password',refCode='KAOS-REF',planId=plan_id),Response()))
    doc=registration.insert_one.call_args.args[0]
    assert doc['requested_membership_plan']==(plan_id or 'free')
    assert doc['referredByCode']=='KAOS-REF'
    assert doc['membership_status']=='EXPIRED' and doc['membership_plan'] is None
    assert doc['role']=='user'
    assert result['requested_membership_plan']==(plan_id or 'free')
    assert 'password_hash' not in result


def test_unknown_membership_does_not_create_an_account(registration):
    with pytest.raises(HTTPException) as error:
        asyncio.run(auth.register(RegisterReq(email='new@example.com',name='New',password='fixture-password',planId='made-up'),Response()))
    assert error.value.status_code==400
    registration.insert_one.assert_not_awaited()


def test_new_google_signup_preserves_choice_and_referral_only_as_preferences(registration):
    result=asyncio.run(auth._google_signin_identity({'email':'new@example.com','sub':'verified-google-fixture','email_verified':True},
        {'planId':'ultimate','refCode':'KAOS-REF'}))
    assert result['requested_membership_plan']=='ultimate'
    assert result['referredByCode']=='KAOS-REF'
    assert result['membership_status']=='EXPIRED' and result['membership_plan'] is None


def test_existing_google_account_is_not_downgraded_or_reattributed(registration):
    user={'id':'existing','email':'existing@example.com','google_id':'google-fixture','membership_status':'ACTIVE','membership_plan':'ultimate','referredByCode':'ORIGINAL'}
    registration.find_one.return_value=user
    result=asyncio.run(auth._google_signin_identity({'email':'existing@example.com','sub':'google-fixture','email_verified':True},{'planId':'free','refCode':'NEW'}))
    assert result['membership_plan']=='ultimate'
    assert result['referredByCode']=='ORIGINAL'
    update=registration.update_one.call_args.args[1]['$set']
    assert 'membership_plan' not in update and 'referredByCode' not in update


def test_public_catalog_uses_current_prices_rates_and_omits_private_fields(monkeypatch):
    plans=[{**billing.DEFAULT_PLANS[0],'amount':5900,'private_setting':'do-not-publish'},
           {**billing.DEFAULT_PLANS[1],'enabled':False}]
    monkeypatch.setattr(billing,'get_plans',AsyncMock(return_value=plans))
    monkeypatch.setattr(billing,'get_setting',AsyncMock(side_effect=lambda key,default=None:default))
    monkeypatch.delenv('STRIPE_SECRET_KEY',raising=False)
    data=asyncio.run(billing.membership_catalog())
    assert [p['id'] for p in data['plans']]==['free','pro']
    assert data['plans'][1]['amount']==5900
    assert data['affiliateRates']['ultimate']==[50,25,5]
    assert data['checkoutEnabled'] is False and data['payoutsEnabled'] is False
    assert 'private_setting' not in str(data) and 'lookup_key' not in str(data)
