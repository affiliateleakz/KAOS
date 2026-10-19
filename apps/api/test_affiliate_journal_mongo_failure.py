"""Mongo-backed failure-injection checks for affiliate journal writes.

Runs against disposable CI MongoDB, never production.
"""
import os
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "kaos_test")
import asyncio
from uuid import uuid4
import pytest
import services_affiliate_ledger as ledger
from db import db

def run(coro):
    return asyncio.run(coro)

@pytest.mark.parametrize("kind", ["payment", "reversal"])
def test_partial_journal_write_requires_reconciliation(monkeypatch, kind):
    async def scenario():
        key = uuid4().hex
        buyer, sponsor = "buyer_"+key, "sponsor_"+key
        event = "checkout:"+key
        from kaos.memberships import Affiliate
        async def members(_buyer):
            return {
                buyer: Affiliate(buyer, "free", sponsor),
                sponsor: Affiliate(sponsor, "pro", None),
            }
        monkeypatch.setattr(ledger, "_members", members)
        await ledger.ensure_indexes()
        real_insert = db.affiliate_ledger_entries.insert_many
        async def fail_insert(*args, **kwargs):
            raise RuntimeError("injected journal write failure")
        monkeypatch.setattr(db.affiliate_ledger_entries, "insert_many", fail_insert)
        try:
            if kind == "payment":
                with pytest.raises(RuntimeError, match="injected"):
                    await ledger.record_payment(event, buyer, {"tier":"pro","id":"pro"},4900)
                persisted=await db.affiliate_ledger_payments.find_one({"event_id":event})
                assert persisted["state"]=="pending_entries"
                with pytest.raises(RuntimeError,match="reconciliation"):
                    await ledger.record_payment(event,buyer,{"tier":"pro","id":"pro"},4900)
                assert await db.affiliate_ledger_entries.count_documents({"event_id":event}) == 0
            else:
                monkeypatch.setattr(db.affiliate_ledger_entries, "insert_many", real_insert)
                await ledger.record_payment(event,buyer,{"tier":"pro","id":"pro"},4900)
                monkeypatch.setattr(db.affiliate_ledger_entries, "insert_many", fail_insert)
                with pytest.raises(RuntimeError,match="injected"):
                    await ledger.record_reversal("rev:"+key,event)
                persisted=await db.affiliate_ledger_reversals.find_one({"reversal_id":"rev:"+key})
                assert persisted["state"]=="pending_entries"
                with pytest.raises(RuntimeError,match="reconciliation"):
                    await ledger.record_reversal("rev:"+key,event)
                assert await db.affiliate_ledger_entries.count_documents({"event_id":"rev:"+key}) == 0
        finally:
            monkeypatch.setattr(db.affiliate_ledger_entries, "insert_many", real_insert)
            await db.affiliate_ledger_entries.delete_many({"event_id":{"$in":[event,"rev:"+key]}})
            await db.affiliate_ledger_payments.delete_many({"event_id":event})
            await db.affiliate_ledger_reversals.delete_many({"reversal_id":"rev:"+key})
    run(scenario())
