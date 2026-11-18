"""Versioned receiver-tier rates. New payments snapshot settings; old entries and refunds retain theirs."""

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field
from pymongo.errors import DuplicateKeyError
from db import db, now_iso
from auth import require_role
from kaos.memberships import RATES

KEY = "affiliate_commission_rates"
TIERS = ("free", "trial", "pro", "ultimate")
DEFAULT = {
    **{k: list(v) for k, v in RATES.items()},
    "free": [0, 0, 0],
    "trial": [0, 0, 0],
}
router = APIRouter(
    prefix="/api/admin/affiliate/commission-rates", tags=["commission settings"]
)
owner = require_role("super_admin")


def validate(value):
    if not isinstance(value, dict) or set(value) != set(TIERS):
        raise ValueError("Provide Free, trial, Pro and Ultimate rates")
    output = {}
    for tier in TIERS:
        row = value[tier]
        if not isinstance(row, list) or len(row) != 3:
            raise ValueError("Each membership needs three referral level percentages")
        output[tier] = []
        for raw in row:
            if isinstance(raw, bool):
                raise ValueError("Rates must be numbers")
            try:
                rate = Decimal(str(raw))
            except InvalidOperation:
                raise ValueError("Rates must be numbers") from None
            if (
                not rate.is_finite()
                or not 0 <= rate <= 100
                or rate != rate.quantize(Decimal("0.01"))
            ):
                raise ValueError(
                    "Percentages must be from 0 to 100 with at most two decimals"
                )
            output[tier].append(float(rate))
    if any(
        output[tier][level] != 0 for tier in ("free", "trial") for level in range(3)
    ):
        raise ValueError(
            "Free and trial memberships cannot receive affiliate commissions"
        )
    # Upline recipients may have different tiers: bound the worst mixed-tier chain.
    if (
        sum(Decimal(str(max(output[t][level] for t in TIERS))) for level in range(3))
        > 100
    ):
        raise ValueError(
            "The maximum rates across Levels 1–3 cannot total more than 100% of a payment"
        )
    return output


async def configuration(database=None):
    database = database if database is not None else db
    row = await database.settings.find_one({"key": KEY})
    if not row:
        return {
            "revision": "default",
            "rates": {k: list(v) for k, v in DEFAULT.items()},
        }
    value = row.get("value") or {}
    if not isinstance(value, dict) or not isinstance(value.get("revision"), str):
        raise HTTPException(503, "Commission settings need owner review")
    try:
        rates = validate(value.get("rates"))
    except ValueError:
        raise HTTPException(
            503, "Commission settings are invalid; owner review is required"
        ) from None
    return {
        "revision": value["revision"],
        "rates": rates,
        "updatedAt": value.get("updatedAt"),
        "updatedBy": value.get("updatedBy"),
        "history": value.get("history", []),
    }


async def rates(database=None):
    return (await configuration(database))["rates"]


class RateUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: str = Field(max_length=128)
    rates: dict


@router.get("")
async def get_rates(response: Response, user=Depends(owner)):
    response.headers["Cache-Control"] = "private, no-store"
    return {
        **await configuration(),
        "payoutsEnabled": (await __import__("affiliate_payouts").availability())[
            "payoutsEnabled"
        ],
        "note": "Applies to new qualifying paid invoices only. Existing commissions, holds, reversals and provider activation are unchanged.",
    }


@router.put("")
async def save_rates(request: RateUpdate, user=Depends(owner)):
    try:
        valid = validate(request.rates)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    previous = await configuration()
    if request.revision != previous["revision"]:
        raise HTTPException(409, "Commission rates changed. Reload before saving.")
    value = {
        "revision": uuid4().hex,
        "rates": valid,
        "updatedAt": now_iso(),
        "updatedBy": user["id"],
        "history": (previous.get("history") or [])[-49:]
        + [
            {
                k: previous.get(k)
                for k in ("revision", "rates", "updatedAt", "updatedBy")
            }
        ],
    }
    row = await db.settings.find_one({"key": KEY})
    if row:
        result = await db.settings.update_one(
            {"_id": row["_id"], "value.revision": request.revision},
            {"$set": {"value": value}},
        )
        if result.modified_count != 1:
            raise HTTPException(409, "Commission rates changed. Reload before saving.")
    else:
        try:
            await db.settings.insert_one({"_id": KEY, "key": KEY, "value": value})
        except DuplicateKeyError:
            raise HTTPException(
                409, "Commission rates changed. Reload before saving."
            ) from None
    # The revision itself carries the editor and effective timestamp. No payout action is taken.
    return {
        **value,
        "payoutsEnabled": (await __import__("affiliate_payouts").availability())[
            "payoutsEnabled"
        ],
    }
