"""KAOS spot-position exit policy (pure, deterministic, read-only).

This module computes an exit recommendation, NOT an exchange order. Inputs must
come from verified Coinbase fills and a current exchange price. It never
interprets Pocket Option binary expiry as a Coinbase spot exit.
"""
from decimal import Decimal, InvalidOperation


def dec(value, label):
    try:
        d = Decimal(str(value))
        if not d.is_finite() or d < 0:
            raise ValueError(label + ' must be nonnegative and finite')
        return d
    except (TypeError, InvalidOperation):
        raise ValueError(label + ' is invalid')


def exit_decision(*, base_size, entry_notional, entry_fees, mark_price,
                  stop_loss_pct, take_profit_pct, estimated_exit_fee_pct='0',
                  signal=None):
    """Return a read-only decision and mark-to-market net estimate.

    pct inputs are 0..100 percentages; fees assumed in quote currency. Caller
    must separately verify actual fee currencies, tradable base balance, and
    Coinbase product increments before placing any order.
    """
    qty = dec(base_size, 'base_size')
    cost = dec(entry_notional, 'entry_notional')
    fees = dec(entry_fees, 'entry_fees')
    price = dec(mark_price, 'mark_price')
    stop = dec(stop_loss_pct, 'stop_loss_pct')
    target = dec(take_profit_pct, 'take_profit_pct')
    fee_pct = dec(estimated_exit_fee_pct, 'estimated_exit_fee_pct')
    if qty <= 0 or cost <= 0 or price <= 0:
        raise ValueError('Cannot evaluate empty or invalid position')
    if not (Decimal('0') < stop < Decimal('100')) or not (Decimal('0') < target < Decimal('100')):
        raise ValueError('Stop and target must be strictly between 0 and 100 percent')
    if fee_pct >= Decimal('100'):
        raise ValueError('Exit fee estimate must be below 100 percent')
    proceeds = qty * price
    est_exit_fee = proceeds * fee_pct / Decimal('100')
    pnl = proceeds - est_exit_fee - cost - fees
    basis = cost + fees
    pct = pnl / basis * Decimal('100')
    # Price-based protective exits, then strategy exit. No AI authority.
    if pct <= -stop:
        reason = 'STOP_LOSS'
    elif pct >= target:
        reason = 'TAKE_PROFIT'
    elif signal == 'SELL':
        reason = 'KAOS_STRATEGY_SELL'
    else:
        reason = 'HOLD'
    return {'action': 'SELL' if reason != 'HOLD' else 'HOLD', 'reason': reason,
            'base_size': str(qty), 'estimated_net_pnl_usd': str(pnl),
            'estimated_net_return_pct': str(pct),
            'execution_enabled': False}
