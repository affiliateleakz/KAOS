"""Offline worker regression tests; no exchange/network orders."""
import asyncio, importlib, sys, types, unittest
from unittest.mock import AsyncMock, patch

class WorkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pymongo=types.ModuleType('pymongo'); pymongo.ReturnDocument=types.SimpleNamespace(AFTER=1)
        errors=types.ModuleType('pymongo.errors'); errors.DuplicateKeyError=type('DuplicateKeyError',(Exception,),{})
        sys.modules['pymongo']=pymongo; sys.modules['pymongo.errors']=errors
        auth=types.ModuleType('auth'); auth.get_current_user=lambda: None;sys.modules['auth']=auth
        dbmod=types.ModuleType('db');dbmod.db=types.SimpleNamespace();dbmod.now_iso=lambda:'2026-10-14T00:00:00Z';sys.modules['db']=dbmod
        service=types.ModuleType('services_trading');service.get_entitlements=AsyncMock(return_value={'botAccess':True});sys.modules['services_trading']=service
        cls.routes=importlib.import_module('routes_coinbase')
        cls.worker=importlib.import_module('coinbase_recovery_worker')
    def test_missing_order_id_requires_manual_review(self):
        d=self.worker.db
        d.broker_connections=types.SimpleNamespace(find_one=AsyncMock(return_value={'verified':True}))
        d.coinbase_order_intents=types.SimpleNamespace(update_one=AsyncMock())
        result=asyncio.run(self.worker.resolve_one({'_id':'i1','user_id':'u','client_order_id':'c'}))
        self.assertEqual(result,'MANUAL_REVIEW_CLIENT_ID')
    def test_worker_calls_fill_reconciliation(self):
        d=self.worker.db
        d.broker_connections=types.SimpleNamespace(find_one=AsyncMock(return_value={'verified':True}))
        d.coinbase_order_intents=types.SimpleNamespace(update_one=AsyncMock())
        intent={'_id':'i1','user_id':'u','client_order_id':'c','order_id':'order-1'}
        with patch.object(self.worker,'make_client') as client, patch.object(self.worker,'reconcile_order',new_callable=AsyncMock) as rec:
            client.return_value.get_order.return_value={'order':{'order_id':'order-1','status':'FILLED'}}
            rec.return_value={'state':'FILLED'}
            result=asyncio.run(self.worker.resolve_one(intent))
        self.assertEqual(result,'FILLED');rec.assert_awaited_once_with('u','c')
    def test_wrong_order_id_fails_closed(self):
        d=self.worker.db
        d.broker_connections=types.SimpleNamespace(find_one=AsyncMock(return_value={'verified':True}))
        intent={'_id':'i1','user_id':'u','client_order_id':'c','order_id':'order-1'}
        with patch.object(self.worker,'make_client') as client:
            client.return_value.get_order.return_value={'order':{'order_id':'other','status':'FILLED'}}
            with self.assertRaises(ValueError):asyncio.run(self.worker.resolve_one(intent))

if __name__=='__main__':unittest.main()
