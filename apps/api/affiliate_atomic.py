"""Opt-in, fail-closed MongoDB transaction mode for affiliate journal writes.

Enable KAOS_AFFILIATE_TXN_MODE=required only with a MongoDB replica set or
sharded cluster supporting multi-document transactions. The existing legacy
mode remains for migration/testing and must not be used for financial launch.
"""
import os
from db import db

def transactions_required():
    return os.getenv("KAOS_AFFILIATE_TXN_MODE", "legacy") == "required"

async def write_payment(payment, entries, database=None):
    db = database if database is not None else globals()["db"]
    if transactions_required():
        async with await db.client.start_session() as session:
            async with session.start_transaction():
                await db.affiliate_ledger_payments.insert_one(
                    {**payment, "state": "completed"}, session=session)
                if entries:
                    await db.affiliate_ledger_entries.insert_many(entries, session=session)
        return
    await db.affiliate_ledger_payments.insert_one({**payment, "state": "pending_entries"})
    if entries:
        await db.affiliate_ledger_entries.insert_many(entries)
    result = await db.affiliate_ledger_payments.update_one(
        {"event_id": payment["event_id"], "state": "pending_entries"},
        {"$set": {"state": "completed"}})
    if result.modified_count != 1:
        raise RuntimeError("Affiliate payment completion could not be confirmed")

async def write_reversal(reversal, payment_event_id, previous_amount, next_amount, entries, database=None):
    db = database if database is not None else globals()["db"]
    if transactions_required():
        async with await db.client.start_session() as session:
            async with session.start_transaction():
                await db.affiliate_ledger_reversals.insert_one(
                    {**reversal, "state": "completed"}, session=session)
                changed = await db.affiliate_ledger_payments.update_one(
                    {"event_id": payment_event_id, "state": "completed",
                     "reversed_amount": previous_amount},
                    {"$set": {"reversed_amount": next_amount}}, session=session)
                if changed.modified_count != 1:
                    raise RuntimeError("Concurrent affiliate reversal: transaction aborted")
                if entries:
                    await db.affiliate_ledger_entries.insert_many(entries, session=session)
        return
    await db.affiliate_ledger_reversals.insert_one({**reversal, "state": "pending_entries"})
    changed = await db.affiliate_ledger_payments.update_one(
        {"event_id": payment_event_id, "reversed_amount": previous_amount},
        {"$set": {"reversed_amount": next_amount}})
    if changed.modified_count != 1:
        raise RuntimeError("Concurrent affiliate reversal requires ledger reconciliation")
    if entries:
        await db.affiliate_ledger_entries.insert_many(entries)
    completed = await db.affiliate_ledger_reversals.update_one(
        {"reversal_id": reversal["reversal_id"], "state": "pending_entries"},
        {"$set": {"state": "completed"}})
    if completed.modified_count != 1:
        raise RuntimeError("Affiliate reversal completion could not be confirmed")
