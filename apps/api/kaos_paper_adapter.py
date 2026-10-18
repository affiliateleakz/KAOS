"""Explicit paper-only adapter for multi-broker integration testing.

Does not connect to exchanges. Never claims an exchange fill.
"""
from __future__ import annotations
from decimal import Decimal
from kaos_broker_core import Capabilities, AssetClass, OrderKind, OrderState, ExecutionReport

class PaperAdapter:
    broker_id = 'kaos_paper'
    capabilities = Capabilities(
        frozenset(AssetClass), frozenset(OrderKind),
        supports_short=True, supports_expiry=True, supports_fills=True,
        live_supported=False)

    def __init__(self):
        self.orders = {}

    async def market_rules(self, symbol):
        return {'symbol': symbol, 'mode': 'PAPER_ONLY'}

    async def submit(self, intent):
        key = (intent.account_id, intent.client_order_id)
        if key in self.orders:
            return self.orders[key]
        report = ExecutionReport(self.broker_id, intent.account_id,
                                 intent.client_order_id, None, OrderState.SUBMITTED)
        self.orders[key] = report
        return report

    async def lookup(self, client_order_id):
        if client_order_id not in self.orders:
            raise KeyError('Unknown paper order')
        return self.orders[client_order_id]

    async def fills(self, broker_order_id):
        return []

    async def balances(self):
        return {}

    async def cancel(self, broker_order_id):
        raise NotImplementedError('Paper order cancellation requires a client order ID')
