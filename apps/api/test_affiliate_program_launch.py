import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
import pytest
from fastapi import HTTPException
import routes_affiliate as aff
import routes_affiliate_connect as connect


def test_referral_link_uses_configured_site_not_request_origin(monkeypatch):
    monkeypatch.setenv('FRONTEND_URL', 'https://tradingwithkaos.com')
    assert aff.referral_link('A&B') == 'https://tradingwithkaos.com/register?ref=A%26B'
    assert aff._code({'id':'one','username':'SAME'}) != aff._code({'id':'two','username':'SAME'})


@pytest.mark.parametrize('user,program,account', [
    ({'id':'u','account_status':'banned'}, {'enabled':True}, None),
    ({'id':'u'}, {'enabled':False}, None),
    ({'id':'u'}, {'enabled':True}, {'status':'suspended'}),
])
def test_enrollment_respects_program_and_account_restrictions(monkeypatch,user,program,account):
    insert=AsyncMock()
    monkeypatch.setattr(aff,'get_program',AsyncMock(return_value=program))
    monkeypatch.setattr(aff,'db',SimpleNamespace(affiliate_accounts=SimpleNamespace(find_one=AsyncMock(return_value=account),insert_one=insert)))
    with pytest.raises(HTTPException):asyncio.run(aff.activate(user))
    insert.assert_not_awaited()


def test_program_rates_come_from_commission_engine(monkeypatch):
    monkeypatch.setattr(aff,'get_program',AsyncMock(return_value={'enabled':True}))
    monkeypatch.setattr(aff.ledger,'member_tier',AsyncMock(return_value='pro'))
    result=asyncio.run(aff.member_program({'id':'u'}))
    assert result['rates']=={'free':[10,0,0],'pro':[30,15,0],'ultimate':[50,25,5]}
    assert result['payoutsEnabled'] is False


def test_stripe_connect_requires_explicit_configuration(monkeypatch):
    monkeypatch.delenv('KAOS_STRIPE_CONNECT_ENABLED',raising=False)
    monkeypatch.setenv('STRIPE_CONNECT_SECRET_KEY','fixture-key')
    with pytest.raises(HTTPException):connect.connect_key()


def test_onboarding_reuses_existing_account_and_never_transfers(monkeypatch):
    monkeypatch.setattr(connect.commerce_providers,'document',AsyncMock(return_value={}))
    monkeypatch.setattr(connect,'active_affiliate',AsyncMock(return_value={'_id':'a','code':'CODE','stripeConnectAccountId':'acct_fixture'}))
    monkeypatch.setattr(connect,'get_program',AsyncMock(return_value={'enabled':True}))
    monkeypatch.setattr(connect,'connect_key',lambda:'fixture-test-key')
    monkeypatch.setenv('FRONTEND_URL','https://tradingwithkaos.com')
    create=Mock(side_effect=AssertionError('Do not create duplicate account'))
    link=Mock(return_value={'url':'https://connect.stripe.com/setup/fixture'})
    transfer=Mock(side_effect=AssertionError('No transfer during onboarding'))
    monkeypatch.setattr(connect.stripe.Account,'create',create)
    monkeypatch.setattr(connect.stripe.AccountLink,'create',link)
    monkeypatch.setattr(connect.stripe.Transfer,'create',transfer)
    result=asyncio.run(connect.onboarding({'id':'u'}))
    assert result['url'].startswith('https://connect.stripe.com/')
    assert link.call_args.kwargs['account']=='acct_fixture'
    assert link.call_args.kwargs['return_url']=='https://tradingwithkaos.com/dashboard/affiliate?connect=return'
    transfer.assert_not_called()
