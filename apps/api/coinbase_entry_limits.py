"""Atomic principal/count reservations across products, without expiring risk locks."""
from decimal import Decimal
from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError


async def reserve(slot,settings,db):
    if not settings:
        await db.coinbase_active_slots.insert_one(slot)
        return
    uid=slot['user_id'];product=slot['product_id'];client_id=slot['client_order_id']
    positions=await db.coinbase_active_slots.find({'user_id':uid}).to_list(5)
    if len(positions)>=settings['chartCount']:raise HTTPException(409,'Selected chart position limit reached')
    if any('reserved_usd' not in p for p in positions):raise HTTPException(409,'Legacy position exposure needs reconciliation')
    amount=int(Decimal(settings['amount'])*100);ceiling=int(Decimal(settings['maxExposureUsd'])*100)
    accounts=db.coinbase_risk_accounts
    try:
        await accounts.update_one({'_id':uid},{'$setOnInsert':{'notional_cents':0,'position_count':0,'products':{}}},upsert=True)
    except DuplicateKeyError:pass  # Another request initialized the natural unique account id.
    # One Mongo update is the authority: concurrent products cannot over-allocate.
    claimed=await accounts.update_one({'_id':uid,'notional_cents':{'$lte':ceiling-amount},
        'position_count':{'$lt':settings['chartCount']},f'products.{product}':{'$exists':False}},
        {'$inc':{'notional_cents':amount,'position_count':1},'$set':{f'products.{product}':client_id}})
    if claimed.modified_count!=1:raise HTTPException(409,'Coinbase bot exposure or position limit reached')
    try:
        await db.coinbase_active_slots.insert_one({**slot,'reserved_usd':settings['amount']})
    except Exception:
        await accounts.update_one({'_id':uid,f'products.{product}':client_id},
            {'$inc':{'notional_cents':-amount,'position_count':-1},'$unset':{f'products.{product}':''}})
        raise


async def release(slot_id,client_id,db):
    """Call only after definitive rejection, no submit, or verified closure."""
    slot=await db.coinbase_active_slots.find_one({'_id':slot_id,'client_order_id':client_id})
    if not slot:return
    if 'reserved_usd' not in slot:raise HTTPException(409,'Unknown exposure reservation; reconcile manually')
    amount=int(Decimal(slot['reserved_usd'])*100);product=slot['product_id']
    await db.coinbase_risk_accounts.update_one({'_id':slot['user_id'],f'products.{product}':client_id},
        {'$inc':{'notional_cents':-amount,'position_count':-1},'$unset':{f'products.{product}':''}})
    await db.coinbase_active_slots.delete_one({'_id':slot_id,'client_order_id':client_id})
