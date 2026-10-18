import unittest
from dataclasses import replace
from kaos_broker_core import OrderIntent, AssetClass, OrderKind, OrderState
from kaos_broker_registry import BrokerRegistry, BrokerUnavailable
from kaos_paper_adapter import PaperAdapter

class RegistryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.registry=BrokerRegistry()
        self.adapter=PaperAdapter()
        self.intent=OrderIntent('u','kaos_paper','acct','client-1','BTC-USD',AssetClass.CRYPTO_SPOT,'BUY',OrderKind.MARKET,'10','QUOTE','sig')
    async def test_unregistered_denied(self):
        with self.assertRaises(BrokerUnavailable): await self.registry.submit(self.intent)
    async def test_disabled_denied(self):
        self.registry.register(self.adapter)
        with self.assertRaises(BrokerUnavailable): await self.registry.submit(self.intent)
    async def test_paper_submits_without_exchange_fill(self):
        self.registry.register(self.adapter,enabled=True)
        result=await self.registry.submit(self.intent)
        self.assertEqual(result.state,OrderState.SUBMITTED)
        self.assertIsNone(result.broker_order_id)
        self.assertEqual(len(self.adapter.orders),1)
    async def test_idempotent_paper(self):
        self.registry.register(self.adapter,enabled=True)
        self.assertEqual(await self.registry.submit(self.intent),await self.registry.submit(self.intent))
        self.assertEqual(len(self.adapter.orders),1)
    async def test_live_denied(self):
        self.registry.register(self.adapter,enabled=True)
        with self.assertRaises(BrokerUnavailable): await self.registry.submit(self.intent,paper=False)
    async def test_mismatched_broker_denied(self):
        self.registry.register(self.adapter,enabled=True)
        with self.assertRaises(BrokerUnavailable): await self.registry.submit(replace(self.intent,broker='coinbase'))
    async def test_invalid_spot_sell_denied(self):
        self.registry.register(self.adapter,enabled=True)
        with self.assertRaises(ValueError): await self.registry.submit(replace(self.intent,side='SELL'))
    async def test_duplicate_registration_denied(self):
        self.registry.register(self.adapter)
        with self.assertRaises(ValueError): self.registry.register(self.adapter)
    async def test_binary_paper(self):
        self.registry.register(self.adapter,enabled=True)
        binary=replace(self.intent,asset_class=AssetClass.BINARY,order_kind=OrderKind.BINARY_DIRECTION,quantity_unit='STAKE',expiration_seconds=15)
        self.assertEqual((await self.registry.submit(binary)).state,OrderState.SUBMITTED)
if __name__=='__main__': unittest.main()
