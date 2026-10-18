"""Offline tests with stubbed DB and Coinbase client; no real orders."""
import asyncio
import sys
import types
import unittest
from unittest.mock import AsyncMock, patch

# Dependencies may not be installed in the isolated test environment.
try:
    import coinbase_position_monitor as monitor
except ImportError:
    import importlib
    fake_db = types.ModuleType('db'); fake_db.db = object()
    fake_routes = types.ModuleType('routes_coinbase')
    fake_routes.connection = AsyncMock(return_value={})
    fake_routes.make_client = lambda _: None
    fake_routes.asdict = lambda x: x
    with patch.dict(sys.modules, {'db': fake_db, 'routes_coinbase': fake_routes}):
        monitor = importlib.import_module('coinbase_position_monitor')


class ProductTests(unittest.TestCase):
    def test_valid_price(self):
        self.assertEqual(monitor.extract_price({'product_id':'BTC-USD','price':'40000.12'}, 'BTC-USD'), '40000.12')
    def test_wrong_product(self):
        with self.assertRaises(ValueError):
            monitor.extract_price({'product_id':'ETH-USD','price':'3000'}, 'BTC-USD')
    def test_bad_price(self):
        for value in ['0','NaN','Infinity','-2',None]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                monitor.extract_price({'product_id':'BTC-USD','price':value}, 'BTC-USD')
    def test_disabled_product(self):
        with self.assertRaises(ValueError):
            monitor.extract_price({'product_id':'BTC-USD','price':'100','trading_disabled':True}, 'BTC-USD')


class MonitorTests(unittest.TestCase):
    def test_read_only_exit_proposal(self):
        async def run():
            slot = types.SimpleNamespace(find_one=AsyncMock(return_value={'_id':'u:coinbase:BTC-USD'}))
            risk = types.SimpleNamespace(find_one=AsyncMock(return_value={
                'stop_loss_pct':'1', 'take_profit_pct':'2', 'estimated_exit_fee_pct':'0', 'enabled':True}))
            proposals = types.SimpleNamespace(update_one=AsyncMock())
            fake = types.SimpleNamespace(coinbase_active_slots=slot,
                coinbase_position_risk=risk, coinbase_position_proposals=proposals)
            intent = {'side':'BUY','state':'FILLED','user_id':'u','product_id':'BTC-USD',
                'client_order_id':'buy1','filled_size':'1','fill_notional':'100', 'fill_fees':'0'}
            class Client:
                def get_product(self, product_id):
                    return {'product_id':product_id,'price':'103'}
            with patch.object(monitor,'db',fake), patch.object(monitor,'connection',new=AsyncMock(return_value={})):
                proposal = await monitor.evaluate_position(intent,client_factory=lambda _:Client())
            self.assertEqual(proposal['decision'],'SELL')
            self.assertEqual(proposal['reason'],'TAKE_PROFIT')
            self.assertFalse(proposal['execution_enabled'])
            proposals.update_one.assert_awaited_once()
        asyncio.run(run())
    def test_missing_risk_fails_closed(self):
        async def run():
            fake = types.SimpleNamespace(
                coinbase_active_slots=types.SimpleNamespace(find_one=AsyncMock(return_value={'_id':'x'})),
                coinbase_position_risk=types.SimpleNamespace(find_one=AsyncMock(return_value=None)))
            intent = {'side':'BUY','state':'FILLED','user_id':'u','product_id':'BTC-USD','client_order_id':'x'}
            with patch.object(monitor,'db',fake):
                with self.assertRaises(ValueError):
                    await monitor.evaluate_position(intent)
        asyncio.run(run())

if __name__ == '__main__': unittest.main()
