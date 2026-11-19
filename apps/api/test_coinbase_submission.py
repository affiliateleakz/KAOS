"""No real orders. Ambiguous provider responses must keep position reservations."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException, Request
from pymongo.errors import DuplicateKeyError
import routes_coinbase as routes


def order_request(side='BUY'):
    return routes.OrderRequest(client_order_id='test-order-1234567890', product_id='BTC-USD', side=side,
        quote_size='10' if side=='BUY' else None, base_size='0.001' if side=='SELL' else None,
        source_buy_client_order_id='source-buy-1234567890' if side=='SELL' else None)


@pytest.mark.parametrize('response', [{}, {'success': True}, {'success': False},
    {'success': 'true', 'success_response': {'order_id': 'exchange-id'}},
    {'success': False, 'error_response': {'message': 'not definitive'}},
    {'success': False, 'error_response': {'error': 'REJECTED'}, 'success_response': {'order_id': 'exchange-id'}},
    {'success': True, 'success_response': {'order_id': 'exchange-id', 'product_id': 'ETH-USD'}},
    {'success': True, 'success_response': {'order_id': 'exchange-id'}, 'error_response': {'error': 'CONFLICT'}}])
def test_ambiguous_or_mismatched_responses_are_not_rejections(response):
    with pytest.raises(ValueError):routes.submission_state(response, order_request())


def test_only_explicit_acceptance_and_rejection_are_definitive():
    assert routes.submission_state({'success': True, 'success_response': {'order_id':'exchange-id'}}, order_request())==('ACCEPTED','exchange-id')
    assert routes.submission_state({'success': False, 'error_response': {'error':'INSUFFICIENT_FUND'}}, order_request())==('REJECTED',None)


@pytest.fixture
def setup(monkeypatch):
    source={'_id':'source-id','state':'FILLED','filled_size':'0.001'}
    intents=SimpleNamespace(find_one=AsyncMock(side_effect=[None,source]), insert_one=AsyncMock(),
                            update_one=AsyncMock(return_value=SimpleNamespace(modified_count=1)))
    slots=SimpleNamespace(insert_one=AsyncMock(),delete_one=AsyncMock())
    monkeypatch.setattr(routes,'db',SimpleNamespace(coinbase_order_intents=intents,coinbase_active_slots=slots))
    monkeypatch.setattr(routes,'authorized',AsyncMock(return_value={'max_order_usd':'25'}))
    monkeypatch.setattr(routes,'connection',AsyncMock(return_value={}))
    client=SimpleNamespace(market_order_buy=Mock(return_value={}),market_order_sell=Mock(return_value={}))
    monkeypatch.setattr(routes,'make_client',Mock(return_value=client))
    request=Request({'type':'http','headers':[]})
    return SimpleNamespace(intents=intents,slots=slots,client=client,request=request)


@pytest.mark.parametrize('side',['BUY','SELL'])
def test_unknown_outcome_never_releases_slot_or_exit_lock(setup,side):
    with pytest.raises(HTTPException) as exc:
        asyncio.run(routes.order(order_request(side),setup.request,{'id':'member-a'}))
    assert exc.value.status_code==502
    setup.slots.delete_one.assert_not_awaited()
    updates=[call.args[1] for call in setup.intents.update_one.call_args_list]
    assert not any('$unset' in update for update in updates)
    assert updates[-1]['$set']['state']=='UNKNOWN_RECONCILIATION_REQUIRED'
    assert setup.intents.insert_one.call_args.args[0]['_id']=='coinbase:member-a:test-order-1234567890'


@pytest.mark.parametrize('failure',[DuplicateKeyError('duplicate'),RuntimeError('database unavailable')])
def test_sell_persistence_failure_releases_only_its_unsubmitted_exit(setup,failure):
    setup.intents.insert_one.side_effect=failure
    with pytest.raises(HTTPException):
        asyncio.run(routes.order(order_request('SELL'),setup.request,{'id':'member-a'}))
    setup.client.market_order_sell.assert_not_called()
    query,update=setup.intents.update_one.call_args.args
    assert query=={'_id':'source-id','state':'EXIT_SUBMITTING','exit_client_order_id':'test-order-1234567890'}
    assert update['$set']['state']=='FILLED' and '$unset' in update


def test_definitive_buy_rejection_releases_reserved_slot(setup):
    setup.client.market_order_buy.return_value={'success':False,'error_response':{'error':'INSUFFICIENT_FUND'}}
    result=asyncio.run(routes.order(order_request(),setup.request,{'id':'member-a'}))
    assert result['state']=='REJECTED'
    setup.slots.delete_one.assert_awaited_once()


def test_stopped_bot_can_reduce_verified_positions_but_cannot_open_new_ones(monkeypatch):
    from datetime import datetime,timezone
    consent={'user_id':'u','enabled':False,'expires_at':datetime(2000,1,1,tzinfo=timezone.utc),
             'bot_settings':{'chartCount':4}}
    monkeypatch.setenv('KAOS_COINBASE_LIVE_ORDERS','enabled')
    monkeypatch.setattr(routes,'get_entitlements',AsyncMock(return_value={'botAccess':False,'chartLimit':1}))
    monkeypatch.setattr(routes,'db',SimpleNamespace(coinbase_live_consent=SimpleNamespace(find_one=AsyncMock(return_value=consent)),
        coinbase_emergency_stops=SimpleNamespace(find_one=AsyncMock(return_value=None))))
    request=SimpleNamespace(headers={'authorization':'Bearer fixture'})
    user={'id':'u','membership_status':'EXPIRED'}
    assert asyncio.run(routes.authorized(request,user,risk_reducing=True))==consent
    with pytest.raises(HTTPException):asyncio.run(routes.authorized(request,user))
