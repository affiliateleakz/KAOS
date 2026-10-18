"""Public disclosed trades scanner. Not a real-time trade feed or an order trigger."""
import os
from datetime import date, datetime, timezone
from secrets import compare_digest
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Literal

from auth import get_current_user
from db import db
from services_trading import get_entitlements

router = APIRouter(prefix="/api/v1/disclosures", tags=["public-disclosures"])
KIND = Literal["house", "senate", "sec_insider", "institutional_13f"]
ACTION = Literal["buy", "sell", "exchange", "grant", "exercise", "holding", "other"]
OFFICIAL_HOSTS = {"disclosures-clerk.house.gov", "efdsearch.senate.gov", "www.sec.gov", "sec.gov"}
# Disclosure categories have different reporting schedules. 13F is a
# quarterly holdings snapshot, NOT an exact buy or sell transaction.
class Disclosure(BaseModel):
    source: KIND
    filing_id: str = Field(min_length=3, max_length=180)
    filer: str = Field(min_length=2, max_length=180)
    ticker: str | None = Field(default=None, max_length=24, pattern=r"^[A-Za-z0-9.:-]+$")
    asset: str = Field(min_length=2, max_length=200)
    action: ACTION
    transaction_date: date | None = None
    filing_date: date
    disclosed_at: datetime
    amount_min_usd: float | None = Field(default=None, ge=0)
    amount_max_usd: float | None = Field(default=None, ge=0)
    source_url: str = Field(max_length=1500)
    note: str = Field(default="", max_length=500)

def validate_disclosure(item: Disclosure):
    if item.source == "house" and os.environ.get("KAOS_HOUSE_DISCLOSURE_RIGHTS") != "approved":
        raise ValueError("House disclosure commercial-use review is required before ingestion")
    parsed = urlparse(item.source_url)
    if parsed.scheme != "https" or parsed.hostname not in OFFICIAL_HOSTS:
        raise ValueError("Official House, Senate or SEC filing link required")
    allowed_hosts = {"house": {"disclosures-clerk.house.gov"}, "senate": {"efdsearch.senate.gov"},
                     "sec_insider": {"www.sec.gov", "sec.gov"}, "institutional_13f": {"www.sec.gov", "sec.gov"}}
    if parsed.hostname not in allowed_hosts[item.source]:
        raise ValueError("Source category must match its official filing host")
    if item.source in ("house", "senate") and item.transaction_date is None:
        raise ValueError("Congressional transaction date is required")
    if item.source == "institutional_13f" and item.action != "holding":
        raise ValueError("13F holdings cannot be treated as executed buys or sells")
    if item.amount_min_usd is not None and item.amount_max_usd is not None and item.amount_min_usd > item.amount_max_usd:
        raise ValueError("Invalid disclosed amount range")
    if item.transaction_date and item.transaction_date > item.filing_date:
        raise ValueError("Transaction date cannot postdate filing")
    if item.filing_date > datetime.now(timezone.utc).date():
        raise ValueError("Future filing date")
    if item.disclosed_at.tzinfo is None or item.disclosed_at.astimezone(timezone.utc) > datetime.now(timezone.utc):
        raise ValueError("Disclosure time must be timezone-aware and not in the future")

async def require_scanner(user=Depends(get_current_user)):
    if not (await get_entitlements(user)).get("scanners"):
        raise HTTPException(403, "Political and Wall Street scanners require scanner access")
    return user

@router.post("/ingest")
async def ingest_disclosures(items: list[Disclosure], x_kaos_collector_key: str | None=Header(default=None)):
    key = os.environ.get("KAOS_COLLECTOR_KEY", "")
    if not key or not x_kaos_collector_key or not compare_digest(key, x_kaos_collector_key):
        raise HTTPException(403, "Collector authentication required")
    if len(items) > 100:
        raise HTTPException(413, "Batch exceeds 100 disclosures")
    # Validate all before writing so rejected batches are not partially imported.
    for item in items:
        try:
            validate_disclosure(item)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
    for item in items:
        record = item.model_dump(mode="json")
        record["ticker"] = record["ticker"].upper() if record["ticker"] else None
        await db.kaos_public_disclosures.update_one(
            {"source": record["source"], "filing_id": record["filing_id"],
             "filer": record["filer"], "asset": record["asset"], "action": record["action"],
             "transaction_date": record["transaction_date"]},
            {"$set": record}, upsert=True)
    return {"accepted": len(items), "research_only": True}

@router.get("/trades")
async def list_disclosures(source: KIND | None=None, ticker: str | None=Query(default=None,max_length=24),
                           limit: int=Query(default=50,ge=1,le=100), user=Depends(require_scanner)):
    query = {}
    if source: query["source"] = source
    if ticker: query["ticker"] = ticker.upper()
    records = await db.kaos_public_disclosures.find(query, {"_id":0}).sort("disclosed_at", -1).limit(limit).to_list(length=limit)
    return {"records": records, "count": len(records), "research_only": True,
            "not_real_time": True, "message": "Reported transactions may be disclosed weeks later; 13F reports show holdings, not executions."}
