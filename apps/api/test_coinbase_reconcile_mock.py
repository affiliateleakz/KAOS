"""Offline regression tests for fill ledger and order reconciliation. No real orders."""
import asyncio
import importlib
import sys
import types
import unittest
from unittest.mock import AsyncMock, patch

class Cursor:
    def __init__(self, items): self.items = items
    async def to_list(self, length): return self.items[:length]

class ReconcileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # This test can run on a clean Python environment without the live SDK.
        pymongo = types.ModuleType('pymongo')
        pymongo.ReturnDocument = types.SimpleNamespace(AFTER=1)
        errors = types.ModuleType('pymongo.errors')
        errors.DuplicateKeyError = type('DuplicateKeyError', (Exception,), {})
        sys.modules['pymongo'] = pymongo
        sys.modules['pymongo.errors'] = errors
        auth = types.ModuleType('auth'); auth.get_current_user = lambda: None
        sys.modules['auth'] = auth
        dbmod = types.ModuleType('db')
        dbmod.db = types.SimpleNamespace()
        dbmod.now_iso = lambda: '2026-10-14T00:00:00Z'
        sys.modules['db'] = dbmod
        svc = types.ModuleType('services_trading')
        svc.get_entitlements = AsyncMock(return_value={'botAccess': True})
        sys.modules['services_trading'] = svc
        cls.mod = importlib.import_module('routes_coinbase')

    def setup_db(self, side='BUY', order_status='FILLED', reported='2', fill_size='2'):
        intent = {'_id': 'id1', 'user_id': 'u', 'broker': 'coinbase',
                  'client_order_id': 'client-1', 'order_id': 'order-1',
                  'product_id': 'BTC-USD', 'side': side}
        if side == 'SELL': intent['source_buy_client_order_id'] = 'buy-1'
        fills = []
        if fill_size is not None:
            fills = [{'user_id': 'u', 'broker': 'coinbase', 'trade_id': 'trade-1',
                      'order_id': 'order-1', 'size': fill_size, 'price': '100',
                      'commission': '0.1', 'product_id': 'BTC-USD', 'side': side}]
        d = self.mod.db
        d.coinbase_order_intents = types.SimpleNamespace(find_one=AsyncMock(return_value=intent),
                                                          update_one=AsyncMock())
        d.coinbase_trade_fills = types.SimpleNamespace(find_one=AsyncMock(return_value=None),
                                                       insert_one=AsyncMock(),
                                                       find=lambda *_args, **_kwargs: Cursor(fills))
        d.coinbase_active_slots = types.SimpleNamespace(delete_one=AsyncMock())
        return intent, fills

    def test_filled_buy_returns_own_client_id_and_totals(self):
        self.setup_db()
        client = types.SimpleNamespace(
            get_order=lambda _id: {'order': {'order_id': 'order-1', 'status': 'FILLED', 'filled_size': '2'}},
            get_fills=lambda **kw: {'fills': [{'order_id': 'order-1', 'trade_id': 'trade-1',
                                              'size': '2', 'price': '100', 'commission': '0.1'}]})
        with patch.object(self.mod, 'connection', new=AsyncMock(return_value={})), patch.object(self.mod, 'make_client', return_value=client):
            result = asyncio.run(self.mod.reconcile_order('u', 'client-1'))
        self.assertEqual(result['client_order_id'], 'client-1')
        self.assertEqual(result['state'], 'FILLED')
        self.assertEqual(result['notional'], '200')
        self.assertEqual(result['fees'], '0.1')

    def test_mismatched_reported_fill_size_fails_closed(self):
        self.setup_db()
        client = types.SimpleNamespace(
            get_order=lambda _id: {'order': {'order_id': 'order-1', 'status': 'FILLED', 'filled_size': '3'}},
            get_fills=lambda **kw: {'fills': [{'order_id': 'order-1', 'trade_id': 'trade-1',
                                              'size': '2', 'price': '100', 'commission': '0.1'}]})
        with patch.object(self.mod, 'connection', new=AsyncMock(return_value={})), patch.object(self.mod, 'make_client', return_value=client):
            with self.assertRaises(self.mod.HTTPException) as ctx:
                asyncio.run(self.mod.reconcile_order('u', 'client-1'))
        self.assertEqual(ctx.exception.status_code, 502)
        self.mod.db.coinbase_active_slots.delete_one.assert_not_awaited()

    def test_missing_exchange_order_id_fails_without_exchange_call(self):
        intent, _ = self.setup_db()
        intent.pop('order_id')
        with self.assertRaises(self.mod.HTTPException) as ctx:
            asyncio.run(self.mod.reconcile_order('u', 'client-1'))
        self.assertEqual(ctx.exception.status_code, 409)

if __name__ == '__main__': unittest.main()
