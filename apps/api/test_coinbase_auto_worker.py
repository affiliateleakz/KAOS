import asyncio,time
from datetime import datetime,timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
import coinbase_auto_worker as worker
from test_coinbase_bot_settings import controls,Cursor
from coinbase_bot_settings import normalize


@pytest.fixture
def setup(monkeypatch):
    settings=controls();settings['chartCount']=1;settings['strategySlots']=settings['strategySlots'][:1]
    session={'_id':'u','state':'RUNNING','session_id':'run1','settings':normalize(settings,['BTC-USD'],4)}
    rows=[{'ts':int(time.time()*1000)-5000,'closeTs':int(time.time()*1000)-1}]*300
    feed=SimpleNamespace(rows=rows,update=lambda *a:rows)
    monkeypatch.setattr(worker,'FEEDS',{'BTC-USD':feed})
    monkeypatch.setattr(worker,'lease',AsyncMock(return_value=True))
    monkeypatch.setattr(worker,'control_enabled',AsyncMock(return_value=True))
    monkeypatch.setattr(worker,'order',AsyncMock(return_value={'state':'ACCEPTED'}))
    monkeypatch.setattr(worker,'evaluate',lambda rows:{'direction':'BUY'})
    intents=[]
    database=SimpleNamespace(users=SimpleNamespace(find_one=AsyncMock(return_value={'id':'u','membership_status':'ACTIVE'})),
        coinbase_order_intents=SimpleNamespace(find=lambda *a:Cursor(intents)),
        coinbase_bot_sessions=SimpleNamespace(find_one=AsyncMock(side_effect=lambda *a:session),update_one=AsyncMock()),
        coinbase_active_slots=SimpleNamespace(find_one=AsyncMock(return_value={'tracked':True})),
        coinbase_bot_signal_claims=SimpleNamespace(insert_one=AsyncMock()))
    monkeypatch.setattr(worker,'db',database)
    def response(url,**kwargs):
        data=({'bid':'100','time':datetime.now(timezone.utc).isoformat()} if url.endswith('/ticker') else [])
        return SimpleNamespace(raise_for_status=lambda:None,json=lambda:data)
    http=SimpleNamespace(get=AsyncMock(side_effect=response))
    return SimpleNamespace(session=session,db=database,intents=intents,http=http,feed=feed)


def test_real_runner_uses_existing_amount_and_strategy_instead_of_placeholder_intelligence(setup):
    asyncio.run(worker.run_session(setup.session,setup.http))
    req,request,user=worker.order.call_args.args
    assert req.side=='BUY' and req.product_id=='BTC-USD' and req.quote_size=='17.25'
    assert user['id']=='u'
    assert setup.db.coinbase_bot_signal_claims.insert_one.await_count==1


@pytest.mark.parametrize('condition',['stopped','uncertain','no_signal','warming','disabled_host','gap'])
def test_no_entry_on_stop_uncertain_outcome_warmup_or_bad_feed(setup,monkeypatch,condition):
    if condition=='stopped':setup.session['state']='STOPPING'
    if condition=='uncertain':setup.intents.append({'side':'BUY','state':'UNKNOWN_RECONCILIATION_REQUIRED','client_order_id':'unknown','product_id':'BTC-USD'})
    if condition=='no_signal':monkeypatch.setattr(worker,'evaluate',lambda rows:None)
    if condition=='warming':setup.feed.update=lambda *a:[]
    if condition=='disabled_host':worker.control_enabled.return_value=False
    if condition=='gap':
        def fail(*args):raise ValueError('trade gap')
        setup.feed.update=fail
    asyncio.run(worker.run_session(setup.session,setup.http))
    worker.order.assert_not_awaited()


def test_sell_is_only_an_exit_of_a_verified_owned_position(setup,monkeypatch):
    monkeypatch.setattr(worker,'evaluate',lambda rows:{'direction':'SELL'})
    asyncio.run(worker.run_session(setup.session,setup.http))
    worker.order.assert_not_awaited()  # No short selling.
    setup.intents.append({'client_order_id':'verified-buy-123456789','side':'BUY','state':'FILLED',
                         'filled_size':'0.1','fill_notional':'10','fill_fees':'0.1','product_id':'BTC-USD'})
    asyncio.run(worker.run_session(setup.session,setup.http))
    req=worker.order.call_args.args[0]
    assert req.side=='SELL' and req.base_size=='0.1' and req.source_buy_client_order_id=='verified-buy-123456789'


def test_risk_exit_survives_a_signal_feed_outage_when_quote_is_still_fresh(setup):
    setup.session['settings']['dailyLossLimit']='1'
    setup.intents.append({'client_order_id':'verified-buy-123456789','side':'BUY','state':'FILLED',
                         'filled_size':'0.1','fill_notional':'20','fill_fees':'0.1','product_id':'BTC-USD'})
    def fail(*args):raise ValueError('trade gap')
    setup.feed.update=fail
    asyncio.run(worker.run_session(setup.session,setup.http))
    assert worker.order.call_args.args[0].side=='SELL'


def test_stale_or_missing_bid_never_creates_an_order(setup):
    setup.http.get.side_effect=lambda *a,**k:SimpleNamespace(raise_for_status=lambda:None,json=lambda:{'bid':'100','time':'2000-01-01T00:00:00Z'})
    with pytest.raises(ValueError):asyncio.run(worker.run_session(setup.session,setup.http))
    worker.order.assert_not_awaited()


@pytest.mark.parametrize('kind,value,accepted',[('application/json',{'liveGatewayEnabled':True},True),
    ('application/json',{'liveGatewayEnabled':False},False),('application/json',{},False),
    ('text/html','Bot Verification',None)])
def test_host_control_check_does_not_infer_enablement_from_http_200(monkeypatch,kind,value,accepted):
    # Fixture replaces the fake control helper installed by setup only in other tests.
    response=SimpleNamespace(headers={'content-type':kind},raise_for_status=lambda:None,json=lambda:value)
    http=SimpleNamespace(get=AsyncMock(return_value=response))
    if accepted is None:
        with pytest.raises(ValueError):asyncio.run(worker.control_enabled(http))
    else:assert asyncio.run(worker.control_enabled(http)) is accepted
