import unittest
from dataclasses import replace
from datetime import datetime, timezone, timedelta
from kaos_broker_core import OrderIntent, AssetClass, OrderKind, Capabilities, OrderState
from kaos_broker_registry import BrokerRegistry
from kaos_paper_adapter import PaperAdapter
from kaos_risk_engine import RiskLimits, RiskSnapshot, RiskRejected, check_order
from kaos_execution_pipeline import PaperExecutionPipeline

NOW=datetime(2026,10,14,tzinfo=timezone.utc)
CAP=PaperAdapter.capabilities

def order(**kw):
    fields=dict(user_id='u', broker='kaos_paper', account_id='demo', client_order_id='kaos_order_123456', symbol='BTC-USD',asset_class=AssetClass.CRYPTO_SPOT,side='BUY',order_kind=OrderKind.MARKET,quantity='20',quantity_unit='QUOTE',strategy_signal_id='signal1')
    fields.update(kw)
    return OrderIntent(**fields)

def snap(**kw):
    fields=dict(now=NOW,quote_timestamp=NOW,quote_price='100',daily_realized_pnl='0',open_exposure='0',open_positions=0,available_quote_balance='50')
    fields.update(kw)
    return RiskSnapshot(**fields)

class RiskTests(unittest.TestCase):
    def test_normal(self): self.assertEqual(check_order(order(),CAP,RiskLimits(),snap())['notional'],'20')
    def test_stale(self):
        with self.assertRaises(RiskRejected): check_order(order(),CAP,RiskLimits(),snap(quote_timestamp=NOW-timedelta(seconds=11)))
    def test_future(self):
        with self.assertRaises(RiskRejected): check_order(order(),CAP,RiskLimits(),snap(quote_timestamp=NOW+timedelta(seconds=1)))
    def test_balance(self):
        with self.assertRaises(RiskRejected): check_order(order(),CAP,RiskLimits(),snap(available_quote_balance='10'))
    def test_exposure(self):
        with self.assertRaises(RiskRejected): check_order(order(),CAP,RiskLimits(),snap(open_exposure='90'))
    def test_order_cap(self):
        with self.assertRaises(RiskRejected): check_order(order(quantity='26'),CAP,RiskLimits(),snap())
    def test_loss_limit(self):
        with self.assertRaises(RiskRejected): check_order(order(),CAP,RiskLimits(),snap(daily_realized_pnl='-20'))
    def test_position_cap(self):
        with self.assertRaises(RiskRejected): check_order(order(),CAP,RiskLimits(),snap(open_positions=4))
    def test_stop(self):
        with self.assertRaises(RiskRejected): check_order(order(),CAP,RiskLimits(),snap(emergency_stopped=True))
    def test_live_denied(self):
        with self.assertRaises(RiskRejected): check_order(order(),CAP,RiskLimits(),snap(),live=True)
    def test_nonfinite(self):
        with self.assertRaises(RiskRejected): check_order(order(quantity='NaN'),CAP,RiskLimits(),snap())
    def test_exit_during_loss_halt(self):
        o=order(side='SELL',quantity='0.2',quantity_unit='BASE',metadata={'source_position_id':'pos1'})
        self.assertTrue(check_order(o,CAP,RiskLimits(),snap(daily_realized_pnl='-100',open_positions=4,available_quote_balance='0'),closing_position=True)['approved'])
    def test_exit_requires_source(self):
        with self.assertRaises(RiskRejected): check_order(order(side='SELL'),CAP,RiskLimits(),snap(),closing_position=True)
    def test_contracts_fail_closed(self):
        with self.assertRaises(RiskRejected): check_order(order(quantity_unit='CONTRACTS'),CAP,RiskLimits(),snap())

class PipelineTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.registry=BrokerRegistry(); self.registry.register(PaperAdapter(),enabled=True,paper_only=True)
        self.pipe=PaperExecutionPipeline(self.registry,RiskLimits())
    async def test_submit_is_not_fill(self):
        report=await self.pipe.submit(order(),snap())
        self.assertEqual(report.state,OrderState.SUBMITTED)
        self.assertIsNone(report.broker_order_id)
    async def test_replay(self):
        a=await self.pipe.submit(order(),snap()); b=await self.pipe.submit(order(),snap())
        self.assertIs(a,b)
    async def test_conflicting_replay(self):
        await self.pipe.submit(order(),snap())
        with self.assertRaises(RiskRejected): await self.pipe.submit(order(quantity='21'),snap())
    async def test_risk_before_submission(self):
        with self.assertRaises(RiskRejected): await self.pipe.submit(order(),snap(emergency_stopped=True))
        self.assertEqual(len(self.registry._adapters['kaos_paper'].adapter.orders),0)

if __name__=='__main__': unittest.main()
