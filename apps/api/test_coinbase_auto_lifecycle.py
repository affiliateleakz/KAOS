"""Real local Mongo + fake Coinbase: Start -> BUY -> fills -> SELL -> Stop.

No network provider is used and no exchange account/credentials exist in this test.
"""
import asyncio,os,time
from datetime import datetime,timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from urllib.parse import urlsplit
from uuid import uuid4
import pytest
from fastapi import Response
from motor.motor_asyncio import AsyncIOMotorClient
import routes_coinbase as gateway
import routes_coinbase_bot as api
import coinbase_auto_worker as worker
from test_coinbase_bot_settings import controls


def test_settings_reach_real_reservations_and_reconciled_positions(monkeypatch):
    uri=os.getenv('MONGO_URL','')
    if urlsplit(uri).hostname not in ('127.0.0.1','localhost') or os.getenv('DB_NAME')!='kaos_test':
        pytest.skip('Requires isolated localhost kaos_test')
    async def scenario():
        client=AsyncIOMotorClient(uri,serverSelectionTimeoutMS=1000)
        name='kaos_test_coinbase_'+uuid4().hex;database=client[name];available=False
        try:
            try:await client.admin.command('ping');available=True
            except Exception:pytest.skip('Local test MongoDB unavailable')
            monkeypatch.setenv('KAOS_COINBASE_LIVE_ORDERS','enabled')
            monkeypatch.delenv('KAOS_COINBASE_MAX_ORDER_USD',raising=False)
            for module in (api,gateway,worker):monkeypatch.setattr(module,'db',database)
            ent=AsyncMock(return_value={'botAccess':True,'chartLimit':1})
            monkeypatch.setattr(api,'get_entitlements',ent);monkeypatch.setattr(gateway,'get_entitlements',ent)
            monkeypatch.setattr(api,'connection',AsyncMock(return_value={}));monkeypatch.setattr(gateway,'connection',AsyncMock(return_value={}))
            sent=[]
            def submit(side,**kwargs):
                sent.append((side,kwargs));return {'success':True,'success_response':{'order_id':side+'-exchange-id'}}
            provider=SimpleNamespace(get_api_key_permissions=lambda:{'can_view':True,'can_trade':True,'can_transfer':False},
                market_order_buy=lambda **kw:submit('BUY',**kw),market_order_sell=lambda **kw:submit('SELL',**kw),
                get_order=lambda order_id:{'order':{'order_id':order_id,'status':'FILLED','filled_size':'0.01'}},
                get_fills=lambda **kw:{'fills':[{'order_id':kw['order_ids'][0],'trade_id':kw['order_ids'][0]+'-fill',
                    'size':'0.01','price':'1725' if kw['order_ids'][0].startswith('BUY') else '1800','commission':'0.01'}]})
            monkeypatch.setattr(api,'make_client',lambda _:provider);monkeypatch.setattr(gateway,'make_client',lambda _:provider)
            monkeypatch.setattr(worker,'lease',AsyncMock(return_value=True));monkeypatch.setattr(worker,'control_enabled',AsyncMock(return_value=True))
            rows=[{'closeTs':int(time.time()*1000)-1}]*300
            monkeypatch.setattr(worker,'FEEDS',{'BTC-USD':SimpleNamespace(rows=rows,update=lambda *a:rows)})
            direction={'value':'BUY'};monkeypatch.setattr(worker,'evaluate',lambda _: {'direction':direction['value']})
            def quote(*args,**kwargs):return SimpleNamespace(raise_for_status=lambda:None,json=lambda:{'bid':'1800','time':datetime.now(timezone.utc).isoformat()})
            http=SimpleNamespace(get=AsyncMock(side_effect=quote))
            user={'id':'test-member','membership_status':'ACTIVE'}
            await database.users.insert_one(user.copy())
            await database.coinbase_worker_leases.insert_one({'_id':'coinbase-auto-v1','heartbeat':time.time()})
            settings=controls();settings['chartCount']=1;settings['strategySlots']=settings['strategySlots'][:1]
            started=await api.start(api.Start(settings=settings,products=['BTC-USD']),Response(),user)
            assert started['settings']['amount']=='17.25' and not sent
            session=await database.coinbase_bot_sessions.find_one({'_id':user['id']})
            await worker.run_session(session,http)
            assert len(sent)==1 and sent[0][0]=='BUY' and sent[0][1]['quote_size']=='17.25'
            account=await database.coinbase_risk_accounts.find_one({'_id':user['id']})
            assert account['notional_cents']==1725 and account['position_count']==1
            direction['value']='SELL'
            await worker.run_session(session,http)
            assert len(sent)==2 and sent[1][0]=='SELL' and sent[1][1]['base_size']=='0.01'
            await worker.run_session(session,http)
            account=await database.coinbase_risk_accounts.find_one({'_id':user['id']})
            assert account['notional_cents']==0 and account['position_count']==0
            assert await database.coinbase_active_slots.count_documents({})==0
            assert await database.coinbase_trade_fills.count_documents({})==2
            assert len(sent)==2  # Reconciliation is not another submit.
            stopped=await api.stop(Response(),user)
            assert stopped['state']=='STOPPING'
            session=await database.coinbase_bot_sessions.find_one({'_id':user['id']})
            await worker.run_session(session,http)
            assert (await database.coinbase_bot_sessions.find_one({'_id':user['id']}))['state']=='STOPPED'
        finally:
            if available:await client.drop_database(name)
            client.close()
    asyncio.run(scenario())
