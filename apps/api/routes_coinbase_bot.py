"""Explicit Start/Stop of server-owned Coinbase automation using existing bot controls."""
import os,time
from decimal import Decimal
from datetime import datetime,timedelta,timezone
from uuid import uuid4
from fastapi import APIRouter,Depends,HTTPException,Response
from pydantic import BaseModel
from auth import get_current_user
from db import db,now_iso
from services_trading import get_entitlements
from coinbase_bot_settings import normalize
from routes_coinbase import connection,make_client,asdict
import asyncio

router=APIRouter(prefix='/api/v1/coinbase-bot',tags=['coinbase-bot'])

class Start(BaseModel):
    settings:dict
    products:list[str]


def private(response):response.headers['Cache-Control']='private, no-store'


@router.get('/status')
async def status(response:Response,user:dict=Depends(get_current_user)):
    private(response)
    row=await db.coinbase_bot_sessions.find_one({'_id':user['id']}) or {}
    worker=await db.coinbase_worker_leases.find_one({'_id':'coinbase-auto-v1'}) or {}
    return {'enabled':os.getenv('KAOS_COINBASE_LIVE_ORDERS')=='enabled',
            'workerReady':0<=time.time()-worker.get('heartbeat',0)<30,
            'state':row.get('state','STOPPED'),'settings':row.get('settings'),
            'warmup':row.get('warmup',{}),'estimatedSessionPnl':row.get('estimated_session_pnl'),
            'detail':row.get('detail',''),'sessionId':row.get('session_id'),
            'realOrders':True,'strategy':'KAOS_STRATEGY_SR1.1'}


@router.post('/start')
async def start(req:Start,response:Response,user:dict=Depends(get_current_user)):
    private(response)
    if os.getenv('KAOS_COINBASE_LIVE_ORDERS')!='enabled':raise HTTPException(403,'Coinbase live gateway is not enabled on hosting')
    if user.get('account_status','active')!='active' or user.get('extension_access_revoked'):raise HTTPException(403,'Account disabled')
    ent=await get_entitlements(user)
    if not ent.get('botAccess') or (not ent.get('roleGranted') and user.get('membership_status') not in ('ACTIVE','TRIAL')):
        raise HTTPException(403,'Active bot membership required')
    try:settings=normalize(req.settings,req.products,int(ent.get('chartLimit') or 1))
    except ValueError as exc:raise HTTPException(422,str(exc)) from None
    ceiling=os.getenv('KAOS_COINBASE_MAX_ORDER_USD')
    if ceiling:
        from coinbase_bot_settings import money
        try:ceiling=money(ceiling,'Server Coinbase ceiling',positive=True)
        except ValueError:raise HTTPException(503,'Server Coinbase order ceiling is invalid') from None
        if Decimal(settings['amount'])>Decimal(ceiling):raise HTTPException(422,'Trade Amount exceeds the configured server Coinbase order ceiling')
    worker=await db.coinbase_worker_leases.find_one({'_id':'coinbase-auto-v1'}) or {}
    if not 0<=time.time()-worker.get('heartbeat',0)<30:raise HTTPException(503,'Coinbase automatic worker is offline; Start has not been accepted')
    if await db.coinbase_active_slots.find_one({'user_id':user['id']}):raise HTTPException(409,'Existing or uncertain Coinbase positions must be resolved before a new session')
    exposure=await db.coinbase_risk_accounts.find_one({'_id':user['id']}) or {}
    if exposure.get('position_count',0)!=0 or exposure.get('notional_cents',0)!=0 or exposure.get('products'):
        raise HTTPException(409,'Outstanding Coinbase exposure reservations require reconciliation')
    client=make_client(await connection(user['id']))
    try:permissions=asdict(await asyncio.to_thread(client.get_api_key_permissions))
    except Exception:raise HTTPException(502,'Could not verify Coinbase trading permissions') from None
    if permissions.get('can_view') is not True or permissions.get('can_trade') is not True or permissions.get('can_transfer') is not False:
        raise HTTPException(403,'Coinbase live trading needs View and Trade permissions with Transfer disabled')
    session_id=uuid4().hex
    # Natural session idempotency: one active run per member, even without startup indexes.
    from pymongo.errors import DuplicateKeyError
    try:
        await db.coinbase_bot_sessions.update_one({'_id':user['id'],'state':{'$nin':['RUNNING','STARTING','STOPPING']}},
            {'$set':{'state':'STARTING','session_id':session_id,'settings':settings,'started_at':now_iso(),
                     'started_at_ms':int(time.time()*1000),'detail':'Waiting for genuine Coinbase closed-candle warmup'}},upsert=True)
    except DuplicateKeyError:raise HTTPException(409,'Coinbase bot is already running or stopping; refresh status') from None
    try:
        await db.coinbase_live_consent.update_one({'_id':user['id']},{'$set':{'user_id':user['id'],'enabled':True,
            'expires_at':datetime.now(timezone.utc)+timedelta(hours=12),'max_order_usd':settings['amount'],
            'bot_settings':settings,'session_id':session_id}},upsert=True)
        changed=await db.coinbase_bot_sessions.update_one({'_id':user['id'],'session_id':session_id,'state':'STARTING'},
            {'$set':{'state':'RUNNING'}})
        if changed.matched_count!=1:
            await db.coinbase_live_consent.update_one({'_id':user['id']},{'$set':{'enabled':False}})
            raise HTTPException(409,'Start was stopped before activation; refresh Coinbase status')
    except HTTPException:
        raise
    except Exception:
        await db.coinbase_bot_sessions.update_one({'_id':user['id'],'session_id':session_id},{'$set':{'state':'STOPPING','detail':'Start was not confirmed; no new entries. Review Coinbase and session status.'}})
        raise HTTPException(503,'Coinbase Start could not be saved') from None
    return {'state':'RUNNING','sessionId':session_id,'settings':settings,'realOrders':True,
            'detail':'Automatic real-money spot trading requested. One position per selected market; binary expiration does not apply.'}


@router.post('/stop')
async def stop(response:Response,user:dict=Depends(get_current_user)):
    private(response)
    await db.coinbase_bot_sessions.update_one({'_id':user['id'],'state':{'$in':['RUNNING','STARTING']}},
        {'$set':{'state':'STOPPING','detail':'New entries stopped. Existing holdings remain under the running worker\'s risk/exit management.'}})
    await db.coinbase_live_consent.update_one({'_id':user['id'],'user_id':user['id']},{'$set':{'enabled':False}})
    return {'state':'STOPPING','detail':'No new buys. This does not cancel accepted orders or immediately liquidate holdings. Review positions in Coinbase.'}
