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
from routes_coinbase import connection,make_client,asdict,OrderRequest,order,reconcile_order
from fastapi import Request
import asyncio

router=APIRouter(prefix='/api/v1/coinbase-bot',tags=['coinbase-bot'])

class Start(BaseModel):
    settings:dict
    products:list[str]
    execution_mode: str = "server"
    spot: dict = {}


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
            'realOrders':True,'executionMode':row.get('execution_mode','server'),'strategy':row.get('settings',{}).get('strategy','KAOS_STRATEGY_SR1.1')}


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
    if req.execution_mode not in ('server','extension'):
        raise HTTPException(422,'Unsupported Coinbase execution mode')
    if req.execution_mode == 'extension':
        from decimal import InvalidOperation
        spot = {}
        for name in ('stopLossPct','takeProfitPct','maxSpreadPct'):
            try:
                value = Decimal(str(req.spot.get(name)))
                if not value.is_finite() or not 0 < value <= 50:raise ValueError()
                spot[name] = str(value)
            except (ValueError, InvalidOperation):
                raise HTTPException(422,'Spot percentages must be greater than zero and at most 50') from None
        settings.update(strategy='KAOS_SPOT_TREND_V1', spot=spot)
    else:
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
                     'started_at_ms':int(time.time()*1000),'execution_mode':req.execution_mode,'detail':'Extension controls Coinbase spot decisions; keep the KAOS window open' if req.execution_mode=='extension' else 'Waiting for genuine Coinbase closed-candle warmup'}},upsert=True)
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
        {'$set':{'state':'STOPPING','detail':'New entries stopped. Existing holdings need continued exit management; keep the extension open for extension-run sessions.'}})
    await db.coinbase_live_consent.update_one({'_id':user['id'],'user_id':user['id']},{'$set':{'enabled':False}})
    return {'state':'STOPPING','detail':'No new buys. Keep the extension open for software exits. This does not cancel accepted orders or immediately liquidate holdings. Review positions in Coinbase.'}


class BrowserOrder(BaseModel):
    session_id: str
    intent: OrderRequest


@router.get('/snapshot')
async def snapshot(response:Response,user:dict=Depends(get_current_user)):
    private(response)
    session=await db.coinbase_bot_sessions.find_one({'_id':user['id']}) or {}
    if not session.get('session_id'):return {'session':None,'orders':[]}
    query={'user_id':user['id'],'broker':'coinbase','bot_session_id':session['session_id']}
    rows=await db.coinbase_order_intents.find(query,{'_id':0}).to_list(1001)
    if len(rows)>1000:raise HTTPException(409,'Session history limit reached; stop and reconcile before continuing')
    # Read/reconcile exchange outcomes only. This handler never submits an order.
    pending=[r for r in rows if r['state'] in ('ACCEPTED','OPEN') and r.get('order_id')]
    for row in pending[:4]:
        await reconcile_order(user['id'],row['client_order_id'])
    if pending:rows=await db.coinbase_order_intents.find(query,{'_id':0}).to_list(1001)
    if session['state']=='STOPPING' and not await db.coinbase_active_slots.find_one({'user_id':user['id']}):
        await db.coinbase_bot_sessions.update_one({'_id':user['id'],'session_id':session['session_id'],'state':'STOPPING'},
            {'$set':{'state':'STOPPED','detail':'Stopped; no tracked open Coinbase positions'}})
        session['state']='STOPPED'
    fields=('client_order_id','product_id','side','state','source_buy_client_order_id',
            'filled_size','fill_notional','fill_fees','updated_at')
    return {'session':{'sessionId':session['session_id'],'state':session['state'],
                      'executionMode':session.get('execution_mode','server'),
                      'settings':session['settings'],'startedAtMs':session.get('started_at_ms',0)},
            'orders':[{k:r[k] for k in fields if k in r} for r in rows]}


@router.post('/browser-order')
async def browser_order(payload:BrowserOrder,request:Request,user:dict=Depends(get_current_user)):
    session=await db.coinbase_bot_sessions.find_one({'_id':user['id'],'session_id':payload.session_id,'execution_mode':'extension'})
    if not session:raise HTTPException(409,'Extension Coinbase session changed; refresh before submitting')
    if payload.intent.product_id not in session['settings']['products']:
        raise HTTPException(403,'Market was not selected for this session')
    if payload.intent.side=='BUY' and (session['state']!='RUNNING' or time.time()*1000-session.get('started_at_ms',0)>=12*3600*1000):
        raise HTTPException(403,'Entry session stopped or expired')
    if payload.intent.side=='SELL':
        source=await db.coinbase_order_intents.find_one({'user_id':user['id'],'client_order_id':payload.intent.source_buy_client_order_id,'bot_session_id':payload.session_id})
        if not source:raise HTTPException(409,'Position does not belong to this Coinbase session')
    # Existing gateway owns authorization, exact sizes, reservations, duplicate IDs,
    # broker permissions, verified fills, and uncertain-outcome handling.
    return await order(payload.intent,request,user)
