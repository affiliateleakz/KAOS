import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timezone
from kaos_broker_registry import BrokerRegistry
from kaos_broker_core import OrderIntent, AssetClass, OrderKind, OrderState
from kaos_paper_adapter import PaperAdapter
from kaos_risk_engine import RiskLimits, RiskSnapshot, RiskRejected
from kaos_paper_journal import PaperOrderJournal, JournalConflict
from kaos_durable_paper_pipeline import DurablePaperPipeline

NOW=datetime(2026,10,14,tzinfo=timezone.utc)
def intent(**kw):
    data=dict(user_id='u',broker='kaos_paper',account_id='a',client_order_id='id-123',symbol='BTC-USD',asset_class=AssetClass.CRYPTO_SPOT,side='BUY',order_kind=OrderKind.MARKET,quantity='10',quantity_unit='QUOTE',strategy_signal_id='s')
    data.update(kw)
    return OrderIntent(**data)
def snapshot(**kw):
    data=dict(now=NOW,quote_timestamp=NOW,quote_price='100',daily_realized_pnl='0',open_exposure='0',open_positions=0,available_quote_balance='100')
    data.update(kw)
    return RiskSnapshot(**data)

class DurableTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/'journal.db'
        self.adapter=PaperAdapter()
        self.registry=BrokerRegistry()
        self.registry.register(self.adapter,enabled=True,paper_only=True)
        self.pipe=DurablePaperPipeline(self.registry,RiskLimits(),PaperOrderJournal(self.path))
    async def asyncTearDown(self): self.tmp.cleanup()
    async def test_restart_replay_does_not_resubmit(self):
        first=await self.pipe.submit(intent(),snapshot())
        self.assertEqual(first.state,OrderState.SUBMITTED)
        restarted=DurablePaperPipeline(self.registry,RiskLimits(),PaperOrderJournal(self.path))
        second=await restarted.submit(intent(),snapshot())
        self.assertEqual(second,first)
        self.assertEqual(len(self.adapter.orders),1)
    async def test_conflicting_id_denied(self):
        await self.pipe.submit(intent(),snapshot())
        with self.assertRaises(RiskRejected): await self.pipe.submit(intent(quantity='12'),snapshot())
    async def test_unknown_fails_closed(self):
        PaperOrderJournal(self.path).reserve(intent())
        with self.assertRaisesRegex(RiskRejected,'UNKNOWN'): await self.pipe.submit(intent(),snapshot())
        self.assertEqual(len(self.adapter.orders),0)
    async def test_risk_rejection_does_not_reserve(self):
        with self.assertRaises(RiskRejected): await self.pipe.submit(intent(),snapshot(emergency_stopped=True))
        self.assertIsNone(PaperOrderJournal(self.path).get(intent()))
    async def test_account_isolation(self):
        await self.pipe.submit(intent(),snapshot())
        await self.pipe.submit(intent(account_id='other'),snapshot())
        self.assertIsNotNone(PaperOrderJournal(self.path).get(intent(account_id='other')))
    async def test_no_live_adapter(self):
        self.registry._adapters['kaos_paper'].paper_only=False
        with self.assertRaises(Exception): await self.pipe.submit(intent(),snapshot())

if __name__=='__main__': unittest.main()
