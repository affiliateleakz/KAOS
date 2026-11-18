"""Live Stripe Connect transfers of matured commissions, with durable reservation and reconciliation.
A transfer is not proof of a bank deposit. Unknown processor outcomes remain reserved.
"""

import asyncio
import hashlib
import os
from contextlib import asynccontextmanager
from datetime import timedelta
from decimal import Decimal
import time
from uuid import UUID, uuid4
import stripe
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ConfigDict
from pymongo.errors import DuplicateKeyError
from db import db, now, now_iso
from auth import require_role
import commerce_providers as providers
from routes_affiliate_connect import account_for_mode

router = APIRouter(
    prefix="/api/admin/affiliate/payouts", tags=["live affiliate payouts"]
)
OWNER = require_role("super_admin")
ALLOCATED = ("reserved", "unknown", "transferred")


async def configuration():
    setup = await providers.document("stripe")
    values = await providers.credentials("stripe", setup)
    key = values.get("connect_secret_key") or values.get("secret_key") or ""
    configured = setup.get("mode") == "live" and key.startswith("sk_live_")
    release = await db.settings.find_one({"key": "affiliate_payout_release"})
    value = (release or {}).get("value") or {}
    return {
        "key": key if configured else "",
        "configured": bool(configured and setup.get("payoutsSelected")),
        "enabled": bool(
            configured
            and setup.get("payoutsSelected")
            and value.get("enabled")
            and value.get("accountingTransactionsRequired")
            and value.get("databaseFingerprint")
            == hashlib.sha256(
                (os.getenv("MONGO_URL", "") + os.getenv("DB_NAME", "")).encode()
            ).hexdigest()
            and value.get("credentialFingerprint")
            == hashlib.sha256(key.encode()).hexdigest()
        ),
        "platform": value.get("platform"),
        "accountingTransactionsRequired": bool(
            value.get("accountingTransactionsRequired")
        ),
        "updatedAt": value.get("updatedAt"),
    }


async def availability():
    config = await configuration()
    return {
        "payoutsEnabled": config["enabled"],
        "configured": config["configured"],
        "provider": "stripe",
        "mode": "live",
        "updatedAt": config["updatedAt"],
        "note": (
            "Live Stripe transfers enabled. Individual account approval, matured USD balance and platform funding are checked for every request."
            if config["enabled"]
            else "Choose live Stripe payouts and save approved credentials, then enable release in Affiliates. No transfer is sent by enabling release."
        ),
    }


async def balance(affiliate_id, as_of=None):
    stamp = (as_of or now()).isoformat()
    rows = await db.affiliate_ledger_entries.aggregate(
        [
            {"$match": {"affiliate_id": affiliate_id}},
            {"$project": {"amount": {"$toDecimal": "$amount"}, "available_at": 1}},
            {
                "$group": {
                    "_id": None,
                    "pending": {
                        "$sum": {
                            "$cond": [
                                {
                                    "$and": [
                                        {"$gte": ["$amount", 0]},
                                        {"$gt": ["$available_at", stamp]},
                                    ]
                                },
                                "$amount",
                                0,
                            ]
                        }
                    },
                    "available": {
                        "$sum": {
                            "$cond": [
                                {
                                    "$or": [
                                        {"$lt": ["$amount", 0]},
                                        {"$lte": ["$available_at", stamp]},
                                    ]
                                },
                                "$amount",
                                0,
                            ]
                        }
                    },
                    "reversed": {
                        "$sum": {"$cond": [{"$lt": ["$amount", 0]}, "$amount", 0]}
                    },
                }
            },
        ],
        maxTimeMS=5000,
    ).to_list(1)
    totals = rows[0] if rows else {}

    def money(value):
        return Decimal(
            str(value.to_decimal() if hasattr(value, "to_decimal") else value)
        ).quantize(Decimal(".01"))

    pending, available, reversed_ = [
        money(totals.get(k, 0)) for k in ("pending", "available", "reversed")
    ]
    payouts = await db.affiliate_payouts.find(
        {"affiliateUserId": affiliate_id, "state": {"$in": list(ALLOCATED)}}
    ).to_list(10000)
    # Never truncate financial allocation silently.
    if len(payouts) >= 10000:
        raise HTTPException(503, "Payout history requires archival reconciliation")
    reserved = Decimal(0)
    transferred = Decimal(0)
    for payout in payouts:
        amount = Decimal(payout["amountCents"] - payout.get("reversedCents", 0)) / 100
        if payout["state"] == "transferred":
            transferred += amount
        else:
            reserved += amount
    return {
        "pending": str(pending),
        "available": str(available - reserved - transferred),
        "reversed": str(reversed_),
        "reserved": str(reserved),
        "paid": str(transferred),
        "transferred": str(transferred),
    }


@asynccontextmanager
async def lock(affiliate):
    claim = uuid4().hex
    try:
        await db.affiliate_payout_locks.update_one(
            {"_id": affiliate, "until": {"$lt": time.time()}},
            {"$set": {"until": time.time() + 300, "owner": claim}},
            upsert=True,
        )
    except DuplicateKeyError:
        raise HTTPException(
            409, "Another payout request is processing for this affiliate"
        ) from None
    try:
        yield
    finally:
        await db.affiliate_payout_locks.update_one(
            {"_id": affiliate, "owner": claim}, {"$set": {"until": 0}}
        )


async def platform(config):
    if not config["key"]:
        raise HTTPException(503, "Matching live Stripe credentials are required")
    try:
        account = await asyncio.to_thread(
            stripe.Account.retrieve, api_key=config["key"]
        )
    except stripe.StripeError:
        raise HTTPException(
            503,
            "Cannot read the live Stripe platform account; check approved live credentials",
        ) from None
    if (
        not account.get("id")
        or not account.get("details_submitted")
        or not account.get("charges_enabled")
    ):
        raise HTTPException(409, "Stripe platform approval is incomplete")
    if config.get("platform") and account["id"] != config["platform"]:
        raise HTTPException(
            409,
            "Stripe platform changed; reconcile the previous account before release",
        )
    return account["id"]


class Release(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool


@router.get("")
async def status(user=Depends(OWNER)):
    rows = (
        await db.affiliate_payouts.find({}, {"_id": 0})
        .sort("createdAt", -1)
        .limit(50)
        .to_list(50)
    )
    return {**await availability(), "requests": rows}


@router.post("/release")
async def release(req: Release, user=Depends(OWNER)):
    config = await configuration()
    if req.enabled and not config["configured"]:
        raise HTTPException(
            409, "Select Stripe payouts in live mode and save live credentials first"
        )
    if req.enabled:
        hello = await db.client.admin.command("hello")
        if not (
            hello.get("setName") or hello.get("msg") == "isdbgrid"
        ) or not hello.get("logicalSessionTimeoutMinutes"):
            raise HTTPException(
                409,
                "Live payouts require a MongoDB replica set or transaction-capable sharded deployment. No funds were sent.",
            )
        if await db.affiliate_ledger_payments.find_one(
            {"state": {"$ne": "completed"}}
        ) or await db.affiliate_ledger_reversals.find_one(
            {"state": {"$ne": "completed"}}
        ):
            raise HTTPException(
                409,
                "Legacy or incomplete journal records require reconciliation before live release",
            )
    account = (
        await platform({**config, "platform": None})
        if req.enabled
        else config.get("platform")
    )
    if req.enabled and await db.affiliate_payouts.find_one(
        {"state": {"$in": ["reserved", "unknown"]}, "platform": {"$ne": account}}
    ):
        raise HTTPException(
            409,
            "Reconcile pending requests on the previous Stripe platform before changing accounts",
        )
    await db.settings.update_one(
        {"_id": "affiliate_payout_release"},
        {
            "$set": {
                "key": "affiliate_payout_release",
                "value": {
                    "enabled": req.enabled,
                    "accountingTransactionsRequired": (
                        True
                        if req.enabled
                        else config["accountingTransactionsRequired"]
                    ),
                    "databaseFingerprint": hashlib.sha256(
                        (os.getenv("MONGO_URL", "") + os.getenv("DB_NAME", "")).encode()
                    ).hexdigest(),
                    "credentialFingerprint": hashlib.sha256(
                        config["key"].encode()
                    ).hexdigest(),
                    "platform": account,
                    "updatedAt": now_iso(),
                    "updatedBy": user["id"],
                },
            }
        },
        upsert=True,
    )
    return await availability()


class PayoutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    requestId: UUID
    affiliateUserId: str = Field(min_length=1, max_length=100)
    amountCents: int = Field(gt=0, le=99999999, strict=True)


async def confirmed(row, transfer):
    destination = transfer.get("destination")
    destination = (
        destination.get("id") if isinstance(destination, dict) else destination
    )
    if (
        not transfer.get("id")
        or transfer.get("livemode") is not True
        or transfer.get("amount") != row["amountCents"]
        or transfer.get("currency") != "usd"
        or destination != row["destination"]
        or (transfer.get("metadata") or {}).get("kaosPayoutId") != row["requestId"]
    ):
        raise HTTPException(
            409,
            "Provider transfer identity needs manual reconciliation; funds remain reserved",
        )
    reversed_cents = transfer.get("amount_reversed", 0)
    if type(reversed_cents) is not int or not 0 <= reversed_cents <= row["amountCents"]:
        raise HTTPException(409, "Provider reversal amount needs reconciliation")
    await db.affiliate_payouts.update_one(
        {"_id": row["requestId"]},
        {
            "$set": {
                "state": "transferred",
                "transferId": transfer["id"],
                "reversedCents": reversed_cents,
                "updatedAt": now_iso(),
            }
        },
    )
    return {
        "requestId": row["requestId"],
        "state": "transferred",
        "transferId": transfer["id"],
        "reversedCents": reversed_cents,
        "note": "Transferred to the affiliate Stripe account. Bank delivery follows Stripe’s payout schedule.",
    }


@router.post("/requests")
async def create(req: PayoutRequest, user=Depends(OWNER)):
    request_id = str(req.requestId)
    config = await configuration()
    if not config["enabled"]:
        raise HTTPException(
            503,
            "Live affiliate payout release is disabled or provider setup is incomplete",
        )
    async with lock(req.affiliateUserId):
        row = await db.affiliate_payouts.find_one({"_id": request_id})
        was_existing = row is not None
        if row:
            if (
                row["affiliateUserId"] != req.affiliateUserId
                or row["amountCents"] != req.amountCents
            ):
                raise HTTPException(
                    409, "Payout request ID reused with different details"
                )
            if row["state"] == "transferred":
                return {k: row[k] for k in ("requestId", "state", "transferId")}
            if row["state"] == "failed":
                raise HTTPException(
                    409,
                    "The provider rejected this request. Create a new request after resolving the failure",
                )
            if time.time() - row["createdAtSeconds"] > 23 * 3600:
                raise HTTPException(
                    409,
                    "The processor idempotency window requires manual reconciliation; do not create a replacement payment",
                )
        else:
            previous = await db.affiliate_payouts.find_one(
                {
                    "affiliateUserId": req.affiliateUserId,
                    "state": {"$in": ["reserved", "unknown"]},
                }
            )
            if previous:
                raise HTTPException(
                    409,
                    "Reconcile the existing pending request before paying this affiliate again",
                )
        account = await platform(config)
        if row and row["platform"] != account:
            raise HTTPException(409, "Payout belongs to a different Stripe platform")
        affiliate = await db.affiliate_accounts.find_one(
            {"userId": req.affiliateUserId, "status": "active"}
        )
        if not affiliate:
            raise HTTPException(409, "An active affiliate payout profile is required")
        destination = account_for_mode(affiliate, "live")
        if not destination:
            raise HTTPException(
                409, "Affiliate must complete live Stripe onboarding first"
            )
        recipient = await asyncio.to_thread(
            stripe.Account.retrieve, destination, api_key=config["key"]
        )
        if (
            recipient.get("id") != destination
            or not recipient.get("payouts_enabled")
            or (recipient.get("capabilities") or {}).get("transfers") != "active"
            or (recipient.get("metadata") or {}).get("kaosUserId")
            != req.affiliateUserId
        ):
            raise HTTPException(
                409, "Affiliate Stripe approval or account identity is incomplete"
            )
        if row and row["destination"] != destination:
            raise HTTPException(
                409, "Payout destination changed; reconcile the original request"
            )
        if not row:
            money = await balance(req.affiliateUserId)
            available = Decimal(money["available"]) * 100
            program = await db.settings.find_one({"key": "affiliate_program"})
            minimum = (
                Decimal(str(((program or {}).get("value") or {}).get("minPayout", 50)))
                * 100
            )
            if req.amountCents < minimum or req.amountCents > available:
                raise HTTPException(
                    409,
                    "Amount is below the minimum or exceeds matured net commissions after holds, refunds and prior transfers",
                )
            # Legacy/cross-currency earnings must be reviewed rather than treated as USD.
            currency_gaps = await db.affiliate_ledger_entries.aggregate(
                [
                    {
                        "$match": {
                            "affiliate_id": req.affiliateUserId,
                            "available_at": {"$lte": now_iso()},
                        }
                    },
                    {"$match": {"$expr": {"$gt": [{"$toDecimal": "$amount"}, 0]}}},
                    {
                        "$lookup": {
                            "from": "affiliate_ledger_payments",
                            "localField": "event_id",
                            "foreignField": "event_id",
                            "as": "payment",
                        }
                    },
                    {
                        "$match": {
                            "$expr": {
                                "$or": [
                                    {"$ne": [{"$size": "$payment"}, 1]},
                                    {
                                        "$ne": [
                                            {"$arrayElemAt": ["$payment.currency", 0]},
                                            "usd",
                                        ]
                                    },
                                    {
                                        "$ne": [
                                            {"$arrayElemAt": ["$payment.state", 0]},
                                            "completed",
                                        ]
                                    },
                                ]
                            }
                        }
                    },
                    {"$limit": 1},
                ],
                maxTimeMS=5000,
            ).to_list(1)
            if currency_gaps:
                raise HTTPException(
                    409,
                    "Legacy or non-USD commissions require currency reconciliation before transfer",
                )
            funding = await asyncio.to_thread(
                stripe.Balance.retrieve, api_key=config["key"]
            )
            usd = sum(
                r.get("amount", 0)
                for r in funding.get("available", [])
                if r.get("currency") == "usd"
            )
            if usd < req.amountCents:
                raise HTTPException(
                    409, "Insufficient available USD funds on the Stripe platform"
                )
            row = {
                "_id": request_id,
                "requestId": request_id,
                "affiliateUserId": req.affiliateUserId,
                "amountCents": req.amountCents,
                "currency": "usd",
                "destination": destination,
                "platform": account,
                "state": "reserved",
                "createdAt": now_iso(),
                "createdAtSeconds": time.time(),
                "createdBy": user["id"],
            }
            try:
                await db.affiliate_payouts.insert_one(row)
            except DuplicateKeyError:
                raise HTTPException(
                    409, "Payout request is already processing; reload its status"
                ) from None
        current = await balance(req.affiliateUserId)
        if Decimal(current["available"]) < 0:
            if not was_existing:
                await db.affiliate_payouts.update_one(
                    {"_id": request_id},
                    {
                        "$set": {
                            "state": "failed",
                            "failureType": "balance_changed_before_provider_call",
                            "updatedAt": now_iso(),
                        }
                    },
                )
            raise HTTPException(
                409,
                "Refunds or balances changed. Reconcile the pending request before retrying a transfer",
            )
        try:
            transfer = await asyncio.wait_for(
                asyncio.to_thread(
                    stripe.Transfer.create,
                    amount=row["amountCents"],
                    currency="usd",
                    destination=row["destination"],
                    transfer_group="kaos-" + request_id,
                    metadata={
                        "kaosPayoutId": request_id,
                        "affiliateUserId": row["affiliateUserId"],
                    },
                    idempotency_key="kaos-affiliate-payout-" + request_id,
                    api_key=config["key"],
                ),
                40,
            )
        except (
            stripe.InvalidRequestError,
            stripe.AuthenticationError,
            stripe.PermissionError,
        ) as exc:
            await db.affiliate_payouts.update_one(
                {"_id": request_id},
                {
                    "$set": {
                        "state": "unknown" if was_existing else "failed",
                        "failureType": type(exc).__name__,
                        "updatedAt": now_iso(),
                    }
                },
            )
            raise HTTPException(
                409,
                "Stripe rejected the transfer. No replacement should be sent until the request status has been reviewed",
            ) from None
        except Exception:
            await db.affiliate_payouts.update_one(
                {"_id": request_id},
                {"$set": {"state": "unknown", "updatedAt": now_iso()}},
            )
            raise HTTPException(
                503,
                "Transfer result is unknown. Funds remain reserved; reconcile this request before another payout",
            ) from None
        return await confirmed(row, transfer)


class Reconcile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    requestId: UUID
    transferId: str | None = Field(
        default=None, max_length=100, pattern="^tr_[A-Za-z0-9]+$"
    )


@router.post("/reconcile")
async def reconcile(req: Reconcile, user=Depends(OWNER)):
    row = await db.affiliate_payouts.find_one({"_id": str(req.requestId)})
    if not row:
        raise HTTPException(404, "Payout request not found")
    config = await configuration()
    if await platform(config) != row["platform"]:
        raise HTTPException(409, "Restore credentials for the original Stripe platform")
    async with lock(row["affiliateUserId"]):
        if row.get("transferId") or req.transferId:
            transfer = await asyncio.to_thread(
                stripe.Transfer.retrieve, row["transferId"], api_key=config["key"]
            )
            return await confirmed(row, transfer)
        transfers = await asyncio.to_thread(
            stripe.Transfer.list,
            destination=row["destination"],
            limit=100,
            api_key=config["key"],
        )
        matching = [
            t
            for t in transfers.get("data", [])
            if (t.get("metadata") or {}).get("kaosPayoutId") == row["requestId"]
        ]
        if len(matching) == 1:
            return await confirmed(row, matching[0])
        if len(matching) > 1:
            raise HTTPException(
                409, "Multiple provider transfers match; manual reconciliation required"
            )
        return {
            "requestId": row["requestId"],
            "state": row["state"],
            "note": "No matching transfer found in the bounded provider page. Absence is not proof of failure; funds remain reserved. Retry the same request only within its idempotency window.",
        }


@router.get("/balance/{affiliate_id}")
async def affiliate_balance(affiliate_id: str, user=Depends(OWNER)):
    if len(affiliate_id) > 100:
        raise HTTPException(422, "Invalid affiliate account")
    return {
        "affiliateUserId": affiliate_id,
        "balance": await balance(affiliate_id),
        "currency": "usd",
    }
