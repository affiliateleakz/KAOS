"""Real MongoDB replica-set tests for the affiliate journal (never production).

The ordinary API CI job uses a standalone MongoDB. These tests only run in
the dedicated local replica-set job with an explicitly named disposable DB.
"""
import os
from uuid import uuid4

import pytest
from pymongo.errors import DuplicateKeyError

import affiliate_atomic as atomic
import services_affiliate_ledger as ledger
from db import db
from test_affiliate_ledger_api import run

pytestmark = pytest.mark.skipif(
    os.getenv("KAOS_AFFILIATE_MONGO_REPLICA_TESTS") != "1",
    reason="Requires the isolated MongoDB replica-set CI job",
)


@pytest.fixture(autouse=True)
def guard_disposable_database(monkeypatch):
    # Never let this integration suite mutate any external or shared database.
    assert os.getenv("DB_NAME") == "kaos_affiliate_txn_ci"
    mongo_url = os.getenv("MONGO_URL", "")
    assert "localhost:27017" in mongo_url or "127.0.0.1:27017" in mongo_url
    assert "replicaSet=rs0" in mongo_url
    monkeypatch.setenv("KAOS_AFFILIATE_TXN_MODE", "required")
    hello = run(db.client.admin.command("hello"))
    assert hello.get("setName") == "rs0" and hello.get("isWritablePrimary")


def test_payment_and_reversal_are_rolled_back_on_real_duplicate_key():
    tag = uuid4().hex
    failed_payment, payment = f"pay:fail:{tag}", f"pay:ok:{tag}"
    reversal = f"rev:fail:{tag}"
    entry_collision, entry_ok = f"entry:collision:{tag}", f"entry:ok:{tag}"

    async def scenario():
        await ledger.ensure_indexes()
        try:
            await db.affiliate_ledger_entries.insert_one(
                {"entry_id": entry_collision, "event_id": f"seed:{tag}"})
            with pytest.raises(DuplicateKeyError):
                await atomic.write_payment(
                    {"event_id": failed_payment, "reversed_amount": "0"},
                    [{"entry_id": entry_collision, "event_id": failed_payment}],
                    database=db)
            assert await db.affiliate_ledger_payments.find_one(
                {"event_id": failed_payment}) is None
            assert await db.affiliate_ledger_entries.count_documents(
                {"event_id": failed_payment}) == 0

            await atomic.write_payment(
                {"event_id": payment, "reversed_amount": "0"},
                [{"entry_id": entry_ok, "event_id": payment}], database=db)
            assert (await db.affiliate_ledger_payments.find_one(
                {"event_id": payment}))["state"] == "completed"

            with pytest.raises(DuplicateKeyError):
                await atomic.write_reversal(
                    {"reversal_id": reversal, "event_id": payment},
                    payment, "0", "10",
                    [{"entry_id": entry_collision, "event_id": reversal}],
                    database=db)
            assert await db.affiliate_ledger_reversals.find_one(
                {"reversal_id": reversal}) is None
            assert (await db.affiliate_ledger_payments.find_one(
                {"event_id": payment}))["reversed_amount"] == "0"
            assert await db.affiliate_ledger_entries.count_documents(
                {"event_id": reversal}) == 0
        finally:
            await db.affiliate_ledger_reversals.delete_many({"reversal_id": reversal})
            await db.affiliate_ledger_payments.delete_many(
                {"event_id": {"$in": [failed_payment, payment]}})
            await db.affiliate_ledger_entries.delete_many(
                {"entry_id": {"$in": [entry_collision, entry_ok]}})

    run(scenario())


def test_real_mongo_reversal_compare_and_swap_rejects_stale_total():
    tag = uuid4().hex
    payment, first, stale = f"pay:cas:{tag}", f"rev:first:{tag}", f"rev:stale:{tag}"

    async def scenario():
        await ledger.ensure_indexes()
        try:
            await atomic.write_payment(
                {"event_id": payment, "reversed_amount": "0"}, [], database=db)
            await atomic.write_reversal(
                {"reversal_id": first, "event_id": payment},
                payment, "0", "5", [], database=db)
            with pytest.raises(RuntimeError, match="Concurrent affiliate reversal"):
                await atomic.write_reversal(
                    {"reversal_id": stale, "event_id": payment},
                    payment, "0", "10", [], database=db)
            assert await db.affiliate_ledger_reversals.count_documents(
                {"reversal_id": first, "state": "completed"}) == 1
            assert await db.affiliate_ledger_reversals.count_documents(
                {"reversal_id": stale}) == 0
            assert (await db.affiliate_ledger_payments.find_one(
                {"event_id": payment}))["reversed_amount"] == "5"
        finally:
            await db.affiliate_ledger_reversals.delete_many(
                {"reversal_id": {"$in": [first, stale]}})
            await db.affiliate_ledger_payments.delete_many({"event_id": payment})

    run(scenario())
