"""Read-only KAOS Coinbase position monitor.

Does not submit orders. Uses verified, fully reconciled BUY intents and
server-side risk settings; refuses to evaluate missing/stale exchange prices.
"""
import asyncio
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from db import db
from routes_coinbase import connection, make_client, asdict
from coinbase_position_policy import exit_decision


def _positive(value):
    try:
        number = Decimal(str(value))
        if not number.is_finite() or number <= 0:
            raise ValueError('invalid number')
        return number
    except (TypeError, InvalidOperation):
        raise ValueError('invalid number')


def extract_price(response, product_id):
    """Reject missing, mismatched, or invalid prices; never invent market data."""
    item = asdict(response)
    item = item.get('product') or item
    if str(item.get('product_id', '')) != product_id:
        raise ValueError('product identity mismatch')
    if item.get('trading_disabled') is True or item.get('is_disabled') is True:
        raise ValueError('product disabled')
    return str(_positive(item.get('price')))


async def evaluate_position(intent, *, client_factory=make_client):
    """Read-only. Persist an exit *recommendation* but never place an order."""
    if intent.get('side') != 'BUY' or intent.get('state') != 'FILLED':
        raise ValueError('requires fully reconciled open BUY')
    uid, product_id = intent['user_id'], intent['product_id']
    if await db.coinbase_active_slots.find_one({'_id': f'{uid}:coinbase:{product_id}',
                                                 'client_order_id': intent['client_order_id']}) is None:
        raise ValueError('no active position slot')
    config = await db.coinbase_position_risk.find_one({'user_id': uid, 'product_id': product_id,
                                                        'enabled': True})
    if not config:
        raise ValueError('explicit position risk settings required')
    conn = await connection(uid)
    def fetch():
        client = client_factory(conn)
        return extract_price(client.get_product(product_id), product_id)
    price = await asyncio.to_thread(fetch)
    result = exit_decision(base_size=intent['filled_size'],
        entry_notional=intent['fill_notional'], entry_fees=intent['fill_fees'],
        mark_price=price, stop_loss_pct=config['stop_loss_pct'],
        take_profit_pct=config['take_profit_pct'],
        estimated_exit_fee_pct=config.get('estimated_exit_fee_pct', '0'),
        signal=None)
    now = datetime.now(timezone.utc)
    # Proposals are informational only; a separate execution worker must
    # recheck fresh price, authorization, balance and increments before selling.
    proposal = {'user_id': uid, 'product_id': product_id,
        'buy_client_order_id': intent['client_order_id'], 'observed_at': now,
        'mark_price': price, 'decision': result['action'], 'reason': result['reason'],
        'estimated_net_pnl_usd': result['estimated_net_pnl_usd'],
        'execution_enabled': False}
    await db.coinbase_position_proposals.update_one(
        {'user_id': uid, 'buy_client_order_id': intent['client_order_id']},
        {'$set': proposal}, upsert=True)
    return proposal


async def cycle(limit=100):
    """Fail each position independently, never trade on monitoring failure."""
    cursor = db.coinbase_order_intents.find({'broker': 'coinbase', 'side': 'BUY',
                                              'state': 'FILLED'}).limit(limit)
    results = {'checked': 0, 'proposed_exits': 0, 'errors': 0}
    async for intent in cursor:
        try:
            proposal = await evaluate_position(intent)
            results['checked'] += 1
            if proposal['decision'] == 'SELL':
                results['proposed_exits'] += 1
        except Exception:
            results['errors'] += 1
    return results
