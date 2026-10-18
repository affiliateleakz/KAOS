import logging
from pymongo.errors import DuplicateKeyError
import os
from datetime import datetime, timezone
from uuid import uuid4
from motor.motor_asyncio import AsyncIOMotorClient

_client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = _client[os.environ["DB_NAME"]]


def now():
    return datetime.now(timezone.utc)


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix="id"):
    return f"{prefix}_{uuid4().hex[:16]}"


def clean(doc):
    """Strip Mongo _id so documents are JSON serializable."""
    if doc is None:
        return None
    doc.pop("_id", None)
    return doc


async def ensure_indexes():
    await db.users.create_index("email", unique=True)
    await db.users.create_index("username", unique=True, sparse=True)
    await db.users.create_index("id", unique=True)
    await db.login_attempts.create_index("identifier")
    await db.login_attempts.create_index("email")
    await db.password_reset_tokens.create_index("expires_at", expireAfterSeconds=0)
    await db.password_reset_tokens.create_index("token_hash", unique=True)
    await db.password_reset_requests.create_index("email")
    await db.password_reset_requests.create_index("created_at", expireAfterSeconds=900)
    await db.sessions.create_index("session_token")
    await db.strategies.create_index("id", unique=True)
    await db.strategies.create_index("ownerUserId")
    await db.strategies.create_index("visibility")
    await db.strategies.create_index("published")
    await db.devices.create_index("id", unique=True)
    for coll, keys in ((db.paper_orders, [("user_id", 1), ("client_order_id", 1)]),
                       (db.paper_signals, [("signal_id", 1)]), (db.paper_sessions, [("user_id", 1)])):
        try:
            await coll.create_index(keys, unique=True)
        except DuplicateKeyError as exc:
            # Never delete trading records automatically; the app still runs, but an operator must dedupe.
            logging.getLogger("kaos.db").error("Unique index on %s not created; duplicate records exist: %s", coll.name, exc)
    await db.devices.create_index("userId")
    await db.webhook_events.create_index("event_id", unique=True)
    await db.notifications.create_index("userId")
    await db.follows.create_index([("followerId", 1), ("followingId", 1)], unique=True)
    await db.trades.create_index("executionAttemptId", unique=True)
    await db.trades.create_index("userId")
    await db.trades.create_index("state")
    await db.signals.create_index("userId")
    await db.signals.create_index([("clientSignalId", 1), ("userId", 1)])
    await db.affiliate_accounts.create_index("code", unique=True)
    await db.affiliate_accounts.create_index("userId", unique=True)
    await db.commissions.create_index("affiliateUserId")
    await db.commissions.create_index("customerUserId")
    await db.trade_events.create_index("eventId", unique=True)
    await db.learning_samples.create_index("sampleId", unique=True)
    await db.ai_predictions.create_index("userId")
    await db.signal_shares.create_index("id", unique=True)

    # Market Intelligence Centre: member-scoped lists, and bounded scanner lookups.
    await db.member_watchlists.create_index([("user_id", 1), ("id", 1)], unique=True)
    await db.member_alerts.create_index([("user_id", 1), ("id", 1)], unique=True)
    await db.kaos_intelligence.create_index([("source", 1), ("event_id", 1)])
    await db.kaos_intelligence.create_index("observed_at")

    await db.coinbase_order_intents.create_index([("user_id", 1), ("broker", 1), ("client_order_id", 1)], unique=True)
    await db.coinbase_order_intents.create_index([("user_id", 1), ("product_id", 1), ("state", 1)])
    await db.coinbase_trade_fills.create_index([("user_id", 1), ("broker", 1), ("trade_id", 1)], unique=True)
    await db.coinbase_live_consent.create_index("user_id")

    # Unique _id in coinbase_active_slots provides atomic per-user/product BUY reservation.
    await db.coinbase_active_slots.create_index([("user_id", 1), ("product_id", 1)])

    await db.coinbase_position_risk.create_index([("user_id", 1), ("product_id", 1)], unique=True)
    await db.coinbase_position_proposals.create_index([("user_id", 1), ("buy_client_order_id", 1)], unique=True)
