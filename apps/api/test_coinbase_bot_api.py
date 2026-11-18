import time
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pymongo.errors import DuplicateKeyError
from auth import get_current_user
import routes_coinbase_bot as routes
from test_coinbase_bot_settings import controls


@pytest.fixture
def setup(monkeypatch):
    monkeypatch.setenv('KAOS_COINBASE_LIVE_ORDERS','enabled')
    db=SimpleNamespace(coinbase_bot_sessions=SimpleNamespace(update_one=AsyncMock(return_value=SimpleNamespace(matched_count=1)),find_one=AsyncMock(return_value=None)),
        coinbase_worker_leases=SimpleNamespace(find_one=AsyncMock(return_value={'heartbeat':time.time()})),
        coinbase_active_slots=SimpleNamespace(find_one=AsyncMock(return_value=None)),
        coinbase_risk_accounts=SimpleNamespace(find_one=AsyncMock(return_value=None)),
        coinbase_live_consent=SimpleNamespace(update_one=AsyncMock()))
    monkeypatch.setattr(routes,'db',db)
    monkeypatch.setattr(routes,'get_entitlements',AsyncMock(return_value={'botAccess':True,'chartLimit':4}))
    monkeypatch.setattr(routes,'connection',AsyncMock(return_value={}))
    provider=SimpleNamespace(get_api_key_permissions=lambda:{'can_view':True,'can_trade':True,'can_transfer':False})
    monkeypatch.setattr(routes,'make_client',lambda _:provider)
    user={'id':'u','membership_status':'ACTIVE'}
    app=FastAPI();app.include_router(routes.router);app.dependency_overrides[get_current_user]=lambda:user
    with TestClient(app) as client:yield SimpleNamespace(client=client,db=db,provider=provider,user=user)


def start(setup,settings=None):
    return setup.client.post('/api/v1/coinbase-bot/start',json={'settings':settings or controls(),'products':['BTC-USD','ETH-USD']})


def test_start_copies_the_existing_bot_limits_and_does_not_submit_orders(setup):
    result=start(setup)
    assert result.status_code==200,result.text
    assert result.headers['cache-control']=='private, no-store'
    assert result.json()['settings']['amount']=='17.25'
    assert result.json()['settings']['maxExposureUsd']=='34.50'
    consent=setup.db.coinbase_live_consent.update_one.call_args.args[1]['$set']
    assert consent['max_order_usd']=='17.25' and consent['enabled']
    assert consent['bot_settings']['dailyLossLimit']=='35'
    assert setup.db.coinbase_bot_sessions.update_one.await_count==2


@pytest.mark.parametrize('condition',['gateway','worker','membership','positions','permissions','duplicate'])
def test_missing_runtime_requirements_never_create_consent(setup,monkeypatch,condition):
    if condition=='gateway':monkeypatch.delenv('KAOS_COINBASE_LIVE_ORDERS')
    if condition=='worker':setup.db.coinbase_worker_leases.find_one.return_value={'heartbeat':0}
    if condition=='membership':setup.user['membership_status']='EXPIRED'
    if condition=='positions':setup.db.coinbase_active_slots.find_one.return_value={'state':'UNKNOWN'}
    if condition=='permissions':setup.provider.get_api_key_permissions=lambda:{'can_view':True,'can_trade':False,'can_transfer':False}
    if condition=='duplicate':setup.db.coinbase_bot_sessions.update_one.side_effect=DuplicateKeyError('active')
    assert start(setup).status_code in (403,409,503)
    setup.db.coinbase_live_consent.update_one.assert_not_awaited()


def test_stop_blocks_entries_without_pretending_to_liquidate_positions(setup):
    response=setup.client.post('/api/v1/coinbase-bot/stop')
    assert response.status_code==200 and response.json()['state']=='STOPPING'
    assert setup.db.coinbase_live_consent.update_one.call_args.args[1]['$set']=={'enabled':False}
    assert setup.db.coinbase_bot_sessions.update_one.call_args.args[1]['$set']['state']=='STOPPING'


def test_bad_control_cannot_fall_back_to_an_arbitrary_order_amount(setup):
    settings=controls();settings.pop('amount')
    assert start(setup,settings).status_code==422
    setup.db.coinbase_live_consent.update_one.assert_not_awaited()


def test_server_ceiling_rejects_instead_of_silently_changing_user_amount(setup,monkeypatch):
    monkeypatch.setenv('KAOS_COINBASE_MAX_ORDER_USD','10')
    response=start(setup)
    assert response.status_code==422 and 'ceiling' in response.text
    setup.db.coinbase_live_consent.update_one.assert_not_awaited()


def test_stop_racing_start_cannot_be_reported_as_success(setup):
    setup.db.coinbase_bot_sessions.update_one.side_effect=[SimpleNamespace(matched_count=1),SimpleNamespace(matched_count=0)]
    assert start(setup).status_code==409
    assert setup.db.coinbase_live_consent.update_one.call_args.args[1]['$set']=={'enabled':False}


def test_orphaned_exposure_is_not_silently_discarded_on_new_start(setup):
    setup.db.coinbase_risk_accounts.find_one.return_value={'position_count':1,'notional_cents':1725}
    assert start(setup).status_code==409
    setup.db.coinbase_live_consent.update_one.assert_not_awaited()


def test_super_admin_role_entitlement_does_not_need_a_paid_subscription(setup,monkeypatch):
    setup.user.update(role='super_admin',membership_status='EXPIRED')
    monkeypatch.setattr(routes,'get_entitlements',AsyncMock(return_value={'botAccess':True,'chartLimit':4,'roleGranted':True}))
    assert start(setup).status_code==200
    monkeypatch.delenv('KAOS_COINBASE_LIVE_ORDERS')
    assert start(setup).status_code==403  # The owner still needs explicit live enablement.
