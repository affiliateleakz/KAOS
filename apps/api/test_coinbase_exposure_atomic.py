"""Actual local Mongo race test. Never connects to a remote/production database."""
import asyncio,os
from uuid import uuid4
from urllib.parse import urlsplit
import pytest
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import HTTPException
from coinbase_entry_limits import reserve,release


def test_concurrent_products_cannot_spend_the_same_available_exposure():
    uri=os.getenv('MONGO_URL','')
    if urlsplit(uri).hostname not in ('localhost','127.0.0.1') or os.getenv('DB_NAME')!='kaos_test':
        pytest.skip('Requires the isolated localhost kaos_test database')
    async def scenario():
        client=AsyncIOMotorClient(uri,serverSelectionTimeoutMS=1000)
        uid='coinbase-risk-test-'+uuid4().hex;db=client.kaos_test;available=False
        try:
            try:
                await db.command('ping');available=True
            except Exception:pytest.skip('Local test MongoDB unavailable')
            settings={'amount':'17.25','chartCount':2,'maxExposureUsd':'17.25'}
            slots=[{'_id':uid+':coinbase:'+p,'user_id':uid,'product_id':p,'client_order_id':'claim-'+p} for p in ('BTC-USD','ETH-USD')]
            outcomes=await asyncio.gather(*(reserve(slot,settings,db) for slot in slots),return_exceptions=True)
            assert sum(value is None for value in outcomes)==1
            assert sum(isinstance(value,HTTPException) for value in outcomes)==1
            account=await db.coinbase_risk_accounts.find_one({'_id':uid})
            assert account['notional_cents']==1725 and account['position_count']==1
            actual=await db.coinbase_active_slots.find({'user_id':uid}).to_list(3)
            assert len(actual)==1
            for _ in range(2):await release(actual[0]['_id'],actual[0]['client_order_id'],db)
            account=await db.coinbase_risk_accounts.find_one({'_id':uid})
            assert account['notional_cents']==0 and account['position_count']==0 and not account['products']
        finally:
            if available:
                await db.coinbase_active_slots.delete_many({'user_id':uid})
                await db.coinbase_risk_accounts.delete_one({'_id':uid})
            client.close()
    asyncio.run(scenario())
