"""Opt-in, fail-closed MongoDB transaction mode for affiliate journal writes.

Enable KAOS_AFFILIATE_TXN_MODE=required only with a MongoDB replica set or
sharded cluster supporting multi-document transactions. The existing legacy
mode remains for migration/testing and must not be used for financial launch.
"""

import os
from db import db


def transactions_required():
    mode = os.getenv("KAOS_AFFILIATE_TXN_MODE", "legacy").strip().lower()
    if mode not in ("legacy", "required"):
        raise RuntimeError("Invalid KAOS_AFFILIATE_TXN_MODE: use required or legacy")
    return mode == "required"


async def should_transact(database):
    if transactions_required():
        return True
    # Once real payouts are enabled, journal transactions remain mandatory even
    # while new transfers are paused. This setting is written only after a
    # transaction-capable deployment has been identified by the owner release.
    if not hasattr(database, "settings"):
        return False
    release = await database.settings.find_one({"key": "affiliate_payout_release"})
    return bool(
        ((release or {}).get("value") or {}).get("accountingTransactionsRequired")
    )


async def write_payment(payment, entries, database=None):
    db = database if database is not None else globals()["db"]
    if await should_transact(db):
        async with await db.client.start_session() as session:
            async with session.start_transaction():
                await db.affiliate_ledger_payments.insert_one(
                    {**payment, "state": "completed"}, session=session
                )
                if entries:
                    await db.affiliate_ledger_entries.insert_many(
                        entries, session=session
                    )
        return
    await db.affiliate_ledger_payments.insert_one(
        {**payment, "state": "pending_entries"}
    )
    if entries:
        await db.affiliate_ledger_entries.insert_many(entries)
    result = await db.affiliate_ledger_payments.update_one(
        {"event_id": payment["event_id"], "state": "pending_entries"},
        {"$set": {"state": "completed"}},
    )
    if result.modified_count != 1:
        raise RuntimeError("Affiliate payment completion could not be confirmed")


async def write_reversal(
    reversal, payment_event_id, previous_amount, next_amount, entries, database=None
):
    db = database if database is not None else globals()["db"]
    if await should_transact(db):
        async with await db.client.start_session() as session:
            async with session.start_transaction():
                await db.affiliate_ledger_reversals.insert_one(
                    {**reversal, "state": "completed"}, session=session
                )
                changed = await db.affiliate_ledger_payments.update_one(
                    {
                        "event_id": payment_event_id,
                        "state": "completed",
                        "reversed_amount": previous_amount,
                    },
                    {"$set": {"reversed_amount": next_amount}},
                    session=session,
                )
                if changed.modified_count != 1:
                    raise RuntimeError(
                        "Concurrent affiliate reversal: transaction aborted"
                    )
                if entries:
                    await db.affiliate_ledger_entries.insert_many(
                        entries, session=session
                    )
        return
    await db.affiliate_ledger_reversals.insert_one(
        {**reversal, "state": "pending_entries"}
    )
    changed = await db.affiliate_ledger_payments.update_one(
        {"event_id": payment_event_id, "reversed_amount": previous_amount},
        {"$set": {"reversed_amount": next_amount}},
    )
    if changed.modified_count != 1:
        raise RuntimeError(
            "Concurrent affiliate reversal requires ledger reconciliation"
        )
    if entries:
        await db.affiliate_ledger_entries.insert_many(entries)
    completed = await db.affiliate_ledger_reversals.update_one(
        {"reversal_id": reversal["reversal_id"], "state": "pending_entries"},
        {"$set": {"state": "completed"}},
    )
    if completed.modified_count != 1:
        raise RuntimeError("Affiliate reversal completion could not be confirmed")
