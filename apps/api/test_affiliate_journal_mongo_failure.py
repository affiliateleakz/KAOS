"""Mongo-backed journal recovery guards, using the API suite's shared event loop."""
import os
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "kaos_test")
import asyncio
from uuid import uuid4
import pytest
from db import db
import services_affiliate_ledger as ledger

# Motor's shared client must never be used from an asyncio.run() loop that closes.
from test_affiliate_ledger_api import run

def test_pending_payment_cannot_be_acknowledged():
    event = "checkout:pending:" + uuid4().hex
    async def scenario():
        await ledger.ensure_indexes()
        try:
            await db.affiliate_ledger_payments.insert_one({
                "event_id":event, "buyer_id":"testbuyer","state":"pending_entries"})
            with pytest.raises(RuntimeError, match="reconciliation"):
                await ledger.record_payment(event,"testbuyer",{"id":"pro","tier":"pro"},4900)
            assert await db.affiliate_ledger_payments.count_documents({"event_id":event}) == 1
        finally:
            await db.affiliate_ledger_payments.delete_many({"event_id":event})
    run(scenario())

def test_pending_reversal_cannot_be_replayed():
    reversal = "reversal:pending:" + uuid4().hex
    async def scenario():
        await ledger.ensure_indexes()
        try:
            await db.affiliate_ledger_reversals.insert_one({
                "reversal_id":reversal,"event_id":"checkout:example","state":"pending_entries"})
            with pytest.raises(RuntimeError,match="reconciliation"):
                await ledger.record_reversal(reversal,"checkout:example")
            assert await db.affiliate_ledger_reversals.count_documents({"reversal_id":reversal}) == 1
        finally:
            await db.affiliate_ledger_reversals.delete_many({"reversal_id":reversal})
    run(scenario())
