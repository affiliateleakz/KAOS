"""Dedicated Coinbase automation process. Never starts inside Passenger.

Uses the exact KAOS SR1.1 signal module on genuine, contiguous Coinbase trades.
Real orders require both enabled server flags and a member's explicit Start.
"""
import asyncio,logging,os,time,socket
from datetime import datetime,timedelta,timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4
import httpx
from fastapi import HTTPException
from pymongo import ReturnDocument
from db import db
from kaos_signature import evaluate
from coinbase_auto_feed import TradeFeed
from routes_coinbase import OrderRequest,order,reconcile_order,connection,make_client,asdict

log=logging.getLogger('kaos.coinbase.auto')
OWNER=f'{socket.gethostname()}:{os.getpid()}:{uuid4().hex}'
FEEDS={}
LEASE='coinbase-auto-v1'
REQUEST=SimpleNamespace(headers={'authorization':'Bearer server-owned-worker'})


async def lease():
    now=datetime.now(timezone.utc)
    query={'_id':LEASE,'$or':[{'expires_at':{'$lte':now}},{'owner':OWNER}]}
    update={'$set':{'owner':OWNER,'expires_at':now+timedelta(seconds=90),'heartbeat':time.time()}}
    row=await db.coinbase_worker_leases.find_one_and_update(query,update,return_document=ReturnDocument.AFTER)
    if row:return True
    try:await db.coinbase_worker_leases.insert_one({'_id':LEASE,**update['$set']});return True
    except Exception:return False


def session_result(intents,marks,session):
    """Realized + bid-marked open P&L; not a guaranteed stop execution price."""
    buys={i['client_order_id']:i for i in intents if i['side']=='BUY'}
    exits={i.get('source_buy_client_order_id'):i for i in intents if i['side']=='SELL' and i['state']=='FILLED'}
    total=Decimal(0);closed=[]
    for key,buy in buys.items():
        if buy['state'] not in ('FILLED','EXIT_SUBMITTING','CLOSED'):continue
        cost=Decimal(buy['fill_notional'])+Decimal(buy['fill_fees'])
        if key in exits:
            sell=exits[key];pnl=Decimal(sell['fill_notional'])-Decimal(sell['fill_fees'])-cost
            closed.append((sell.get('updated_at',''),pnl))
        else:
            if buy['product_id'] not in marks:raise ValueError('Missing fresh mark for open position')
            pnl=Decimal(buy['filled_size'])*marks[buy['product_id']]-cost
        total+=pnl
    closed.sort();streak=0
    for _,pnl in reversed(closed):
        if pnl<0:streak+=1
        else:break
    s=session['settings'];loss=Decimal(s['dailyLossLimit']);target=Decimal(s['profitTarget'])
    halt=(loss>0 and total<=-loss) or (target>0 and total>=target) or (s['maxLossStreak']>0 and streak>=s['maxLossStreak'])
    cooldown=s['cooldownAfterLoss']
    if s['autoCooldownOn']:
        cooldown=max(cooldown,3600 if streak>=8 else 900 if streak>=5 else 300 if streak>=3 else 0)
    last_loss=next((stamp for stamp,pnl in reversed(closed) if pnl<0),None)
    cooling=bool(last_loss and time.time()-datetime.fromisoformat(last_loss.replace('Z','+00:00')).timestamp()<cooldown)
    return total,halt,cooling


async def control_enabled(http,amount=None):
    from urllib.parse import urlsplit
    origin=os.getenv('KAOS_COINBASE_CONTROL_ORIGIN','https://api.tradingwithkaos.com').rstrip('/')
    parsed=urlsplit(origin)
    if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment:
        raise ValueError('Invalid Coinbase control origin')
    response=await http.get(origin+'/api/v1/coinbase-live/capabilities')
    response.raise_for_status()
    if response.headers.get('content-type','').split(';')[0]!='application/json':raise ValueError('Coinbase control API is not returning JSON')
    data=response.json()
    if not isinstance(data,dict) or data.get('liveGatewayEnabled') is not True:return False
    if amount is not None and data.get('maxOrderUsd') is not None:
        ceiling=Decimal(str(data['maxOrderUsd']))
        if not ceiling.is_finite() or ceiling<=0:raise ValueError('Invalid hosted Coinbase order ceiling')
        if Decimal(amount)>ceiling:return False
    return True


async def run_session(session,http):
    uid=session['_id'];user=await db.users.find_one({'id':uid})
    if not user:raise ValueError('Member unavailable')
    if session.get('started_at_ms') and time.time()*1000-session['started_at_ms']>=12*3600*1000 and session['state']=='RUNNING':
        await db.coinbase_bot_sessions.update_one({'_id':uid,'session_id':session['session_id']},{'$set':{'state':'STOPPING','detail':'Entry consent expired; managing existing holdings only'}})
        session={**session,'state':'STOPPING'}
    settings=session['settings'];signals={};marks={};mark_times={};feed_issues=[]
    for product in settings['products']:
        if not await lease():return
        feed=FEEDS.setdefault(product,TradeFeed());rows=[]
        try:
            response=await http.get(f'https://api.exchange.coinbase.com/products/{product}/trades',params={'limit':1000})
            response.raise_for_status()
            rows=feed.update(response.json(),int(time.time()*1000))
        except Exception:
            feed_issues.append(product)
        # A signal-feed outage must not prevent risk exits if genuine quotes still work.
        ticker=await http.get(f'https://api.exchange.coinbase.com/products/{product}/ticker')
        ticker.raise_for_status();tick=ticker.json()
        stamp=datetime.fromisoformat(tick['time'].replace('Z','+00:00')).timestamp()
        bid=Decimal(str(tick['bid']))
        if not bid.is_finite() or bid<=0 or not 0<=time.time()-stamp<15:raise ValueError('Coinbase quote is stale or invalid')
        marks[product]=bid;mark_times[product]=stamp
        # No old-bar execution or reused signal while a feed has stopped advancing.
        if len(rows)>=300 and 0<=time.time()*1000-rows[-1]['closeTs']<10000:
            signal=evaluate(rows)
            if signal:signals[product]=(rows[-1]['closeTs'],signal['direction'])
    intents=await db.coinbase_order_intents.find({'user_id':uid,'broker':'coinbase','bot_session_id':session['session_id']}).to_list(10001)
    if len(intents)>10000:raise ValueError('Session order review limit reached')
    for intent in intents:
        if intent['state'] in ('ACCEPTED','OPEN') and intent.get('order_id'):
            if not await lease():return
            await reconcile_order(uid,intent['client_order_id'])
    intents=await db.coinbase_order_intents.find({'user_id':uid,'broker':'coinbase','bot_session_id':session['session_id']}).to_list(10001)
    if any(not 0<=time.time()-stamp<15 for stamp in mark_times.values()):raise ValueError('Portfolio marks became stale')
    pnl,halt,cooling=session_result(intents,marks,session)
    if halt:
        await db.coinbase_bot_sessions.update_one({'_id':uid,'session_id':session['session_id']},
            {'$set':{'state':'STOPPING','detail':'Configured session risk limit reached; closing verified holdings'}})
    await db.coinbase_bot_sessions.update_one({'_id':uid,'session_id':session['session_id']},
        {'$set':{'estimated_session_pnl':str(pnl),'worker_checked_at':time.time(),
                 'warmup':{p:len(FEEDS[p].rows) for p in settings['products']},
                 'detail':('Session risk limit reached; managing exits' if halt else
                           'Coinbase closed-candle warmup: '+', '.join(p+' '+str(len(FEEDS[p].rows))+'/300' for p in settings['products']))}})
    uncertain=any(i['state'] in ('SUBMITTING','UNKNOWN_RECONCILIATION_REQUIRED','PARTIAL_FILL_REVIEW','FILL_MISMATCH_REVIEW','EXIT_QUANTITY_REVIEW') for i in intents)
    for product in settings['products']:
        current=await db.coinbase_bot_sessions.find_one({'_id':uid,'session_id':session['session_id']})
        if not current or not await lease():return
        open_buys=[i for i in intents if i['product_id']==product and i['side']=='BUY' and i['state']=='FILLED']
        stamp,direction=signals.get(product,(None,None))
        if stamp is not None and not 0<=time.time()*1000-stamp<10000:direction=None
        # Spot SELL is an exit of a verified KAOS holding; never a short or binary expiry.
        if open_buys and (halt or direction=='SELL'):
            buy=open_buys[0];cid='cbexit_'+buy['client_order_id'][-48:]
            if not await control_enabled(http):return
            if not 0<=time.time()-mark_times[product]<15:raise ValueError('Exit quote became stale')
            if not halt and not 0<=time.time()*1000-stamp<10000:continue
            user=await db.users.find_one({'id':uid})
            if not user:raise ValueError('Member unavailable before exit')
            result=await order(OrderRequest(client_order_id=cid,product_id=product,side='SELL',
                base_size=buy['filled_size'],source_buy_client_order_id=buy['client_order_id']),REQUEST,user)
        elif direction=='BUY' and not open_buys and not uncertain and not halt and not cooling and not feed_issues and current['state']=='RUNNING':
            # Persistent candle identity prevents duplicate signals after process restarts.
            key=f'{uid}:{session["session_id"]}:{product}:{stamp}'
            from pymongo.errors import DuplicateKeyError
            try:await db.coinbase_bot_signal_claims.insert_one({'_id':key,'created_at':time.time()})
            except DuplicateKeyError:continue
            if not await control_enabled(http,settings['amount']):return
            if not 0<=time.time()*1000-stamp<10000 or not 0<=time.time()-mark_times[product]<15:continue
            user=await db.users.find_one({'id':uid})
            if not user:raise ValueError('Member unavailable before entry')
            result=await order(OrderRequest(client_order_id='cbauto_'+uuid4().hex,product_id=product,side='BUY',quote_size=settings['amount']),REQUEST,user)
        else:continue
        if result.get('state')=='REJECTED':
            await db.coinbase_bot_sessions.update_one({'_id':uid,'session_id':session['session_id']},
                {'$set':{'state':'STOPPING','detail':'Coinbase rejected an order; new entries stopped. Review the account and order settings.'}})
            return
    if current['state']=='STOPPING' and not await db.coinbase_active_slots.find_one({'user_id':uid}):
        await db.coinbase_bot_sessions.update_one({'_id':uid,'session_id':session['session_id']},{'$set':{'state':'STOPPED','detail':'Stopped; no tracked open Coinbase positions'}})


async def cycle(http):
    if not await control_enabled(http) or not await lease():return
    async for session in db.coinbase_bot_sessions.find({'state':{'$in':['RUNNING','STOPPING']},'execution_mode':{'$ne':'extension'}}).limit(100):
        try:await run_session(session,http)
        except Exception as exc:
            log.warning('Coinbase automatic cycle paused (%s)',type(exc).__name__)
            await db.coinbase_bot_sessions.update_one({'_id':session['_id'],'session_id':session['session_id']},
                {'$set':{'detail':'Market/order check unavailable; no replacement orders. Check Coinbase and diagnostics.','last_error_type':type(exc).__name__,
                         **({'state':'STOPPING'} if isinstance(exc,HTTPException) else {})}})


async def main():
    if os.getenv('KAOS_COINBASE_AUTO_WORKER')!='enabled' or os.getenv('KAOS_COINBASE_LIVE_ORDERS')!='enabled':
        raise SystemExit('Coinbase automatic worker and live gateway must both be explicitly enabled')
    logging.basicConfig(level=logging.INFO)
    async with httpx.AsyncClient(timeout=10,headers={'User-Agent':'KAOS-Coinbase-Auto/1.0'}) as http:
        while True:
            try:await cycle(http)
            except Exception as exc:log.warning('Coinbase control check unavailable (%s); no orders',type(exc).__name__)
            await asyncio.sleep(5)


if __name__=='__main__':asyncio.run(main())
