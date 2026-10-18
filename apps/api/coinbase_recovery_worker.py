"""KAOS Coinbase recovery worker (read-only exchange operations).

Polls previously submitted orders; never creates BUY/SELL orders. Distributed
Mongo lease ensures only one worker runs per deployment. Fail-closed: errors
are recorded for review and never trigger a retry of an ambiguous order.
Run: python coinbase_recovery_worker.py (separate from web workers).
"""
import asyncio
import logging
import os
import socket
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from pymongo import ReturnDocument
from db import db
from routes_coinbase import make_client, asdict, reconcile_order, release_exit_lock

log = logging.getLogger('kaos.coinbase.recovery')
OWNER = f'{socket.gethostname()}:{os.getpid()}:{uuid4().hex}'
LEASE_ID = 'coinbase-recovery-v1'


def utcnow():
    return datetime.now(timezone.utc)


async def acquire_lease(seconds=90):
    now = utcnow()
    query = {'_id': LEASE_ID, '$or': [{'expires_at': {'$lte': now}}, {'owner': OWNER}]}
    update = {'$set': {'owner': OWNER, 'expires_at': now + timedelta(seconds=seconds)}}
    lease = await db.coinbase_worker_leases.find_one_and_update(
        query, update, return_document=ReturnDocument.AFTER)
    if lease:
        return True
    try:
        await db.coinbase_worker_leases.insert_one({'_id': LEASE_ID, 'owner': OWNER,
            'expires_at': now + timedelta(seconds=seconds)})
        return True
    except Exception:
        # Concurrent worker acquired the lease; DB outage must fail closed.
        return False


MANUAL_REVIEW_AFTER = timedelta(minutes=10)
STALE_EXIT_LOCK = timedelta(minutes=2)


def _older_than(ts, age):
    if not ts:
        return True
    t = datetime.fromisoformat(str(ts).replace('Z', '+00:00'))
    return utcnow() - (t if t.tzinfo else t.replace(tzinfo=timezone.utc)) > age


def find_by_client_id(client, intent):
    """Page Coinbase orders for the product since the intent was created; return the order_id with our client ID."""
    cursor, pages = None, 0
    while pages < 20:
        args = {'product_ids': [intent['product_id']], 'limit': 250}
        if intent.get('created_at'):
            args['start_date'] = str(intent['created_at'])[:19] + 'Z'
        if cursor:
            args['cursor'] = cursor
        page = asdict(client.list_orders(**args))
        for o in page.get('orders') or []:
            o = asdict(o)
            if o.get('client_order_id') == intent['client_order_id']:
                return str(o['order_id'])
        cursor, pages = page.get('cursor'), pages + 1
        if not page.get('has_next') or not cursor:
            return None
    raise ValueError('Too many order pages; manual review')


async def release_stale_exit_locks():
    """A crash between locking a position for exit and saving the SELL intent leaves EXIT_SUBMITTING with no
    intent. No exchange call can have happened (the intent is saved first), so the lock is released."""
    released = 0
    async for src in db.coinbase_order_intents.find({'broker': 'coinbase', 'state': 'EXIT_SUBMITTING'}).limit(100):
        if not _older_than(src.get('exit_locked_at'), STALE_EXIT_LOCK):
            continue
        if await db.coinbase_order_intents.find_one({'user_id': src['user_id'], 'broker': 'coinbase',
                                                     'client_order_id': src.get('exit_client_order_id')}):
            continue
        await release_exit_lock(src['user_id'], src['client_order_id'], src.get('exit_client_order_id'))
        released += 1
    return released


async def resolve_one(intent):
    """Only read Coinbase order state. Never infer UNKNOWN as rejected."""
    uid = intent['user_id']
    conn = await db.broker_connections.find_one({'user_id': uid, 'broker': 'coinbase', 'verified': True})
    if not conn:
        raise ValueError('No verified connection')
    if not intent.get('order_id'):
        # An ambiguous submit may have succeeded: look the order up by our client ID at Coinbase.
        found = await asyncio.to_thread(find_by_client_id, make_client(conn), intent)
        if found:
            await db.coinbase_order_intents.update_one({'_id': intent['_id']}, {'$set': {
                'order_id': found, 'recovery_status': 'ORDER_ID_RECOVERED', 'recovery_checked_at': utcnow()}})
            intent = {**intent, 'order_id': found}
        else:
            # Absence from a listing is not proof the broker never accepted the order (listings can be
            # incomplete or eventually consistent, and a late fill is possible). Keep the state and the
            # risk lock; an operator resolves it after checking the broker directly.
            status = ('NOT_IN_LISTING_MANUAL_REVIEW' if _older_than(intent.get('created_at'), MANUAL_REVIEW_AFTER)
                      else 'WAITING_FOR_EXCHANGE')
            await db.coinbase_order_intents.update_one({'_id': intent['_id']}, {'$set': {
                'recovery_status': status, 'recovery_checked_at': utcnow()}})
            return status
    def read():
        client = make_client(conn)
        obj = asdict(client.get_order(intent['order_id']))
        order = obj.get('order') or obj
        if str(order.get('order_id')) != str(intent['order_id']):
            raise ValueError('Coinbase order ID mismatch')
        return order
    order = await asyncio.to_thread(read)
    status = str(order.get('status', '')).upper()
    await db.coinbase_order_intents.update_one({'_id': intent['_id']}, {'$set': {
        'recovery_exchange_status': status, 'recovery_checked_at': utcnow(),
        'recovery_status': 'FILL_RECONCILIATION_REQUIRED'}})
    # The shared reconciliation routine validates fills and persists the ledger.
    # It may release a slot only after a fully verified exit.
    result = await reconcile_order(uid, intent['client_order_id'])
    await db.coinbase_order_intents.update_one({'_id': intent['_id']}, {'$set': {
        'recovery_status': 'RECONCILED', 'recovery_checked_at': utcnow()}})
    return result['state']


async def cycle():
    if not await acquire_lease():
        return 0
    states = ['SUBMITTING', 'ACCEPTED', 'UNKNOWN_RECONCILIATION_REQUIRED',
              'OPEN', 'PARTIAL_FILL_REVIEW', 'FILL_MISMATCH_REVIEW']
    cursor = db.coinbase_order_intents.find({'broker': 'coinbase', 'state': {'$in': states}}).limit(100)
    await release_stale_exit_locks()
    count = 0
    async for intent in cursor:
        # Renew before each operation. A second worker may have acquired lease.
        if not await acquire_lease():
            break
        try:
            await resolve_one(intent)
        except Exception as exc:
            log.warning('Recovery check failed for order %s: %s', intent.get('client_order_id'), type(exc).__name__)
            await db.coinbase_order_intents.update_one({'_id': intent['_id']}, {'$set': {
                'recovery_status': 'MANUAL_REVIEW_ERROR', 'recovery_checked_at': utcnow()}})
        count += 1
    return count


async def main():
    if os.getenv('KAOS_COINBASE_RECOVERY_WORKER', 'disabled') != 'enabled':
        raise SystemExit('Recovery worker disabled; set KAOS_COINBASE_RECOVERY_WORKER=enabled')
    logging.basicConfig(level=logging.INFO)
    while True:
        try:
            await cycle()
            if os.getenv('KAOS_COINBASE_POSITION_MONITOR', 'disabled') == 'enabled':
                # The position monitor is read-only and shares this worker's lease.
                if await acquire_lease():
                    from coinbase_position_monitor import cycle as monitor_positions
                    await monitor_positions()
        except Exception:
            log.exception('Recovery/monitoring cycle failed; no orders will be submitted')
        await asyncio.sleep(max(15, int(os.getenv('KAOS_COINBASE_RECOVERY_INTERVAL_SEC', '30'))))


if __name__ == '__main__':
    asyncio.run(main())
