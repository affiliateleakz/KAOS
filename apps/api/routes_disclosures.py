"""Public disclosed trades scanner. Not a real-time trade feed or an order trigger."""
import asyncio
import os
import time
from datetime import date, datetime, timezone
from secrets import compare_digest
from urllib.parse import urlencode, urlparse
from xml.etree import ElementTree

import httpx

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

# Free, keyless headline discovery for the political + Wall Street research view.
# Google News RSS is a public feed: no account, no key, one cached request per topic.
HEADLINE_TOPICS = {
    "politics": 'congress stock trades OR politician stocks OR congressional trading',
    "wallstreet": 'insider trading OR "wall street" SEC filing OR hedge fund disclosure',
    "markets": '"stock market" OR earnings OR "Federal Reserve" markets',
}
_HEADLINE_CACHE: dict = {}
_HEADLINE_TTL = 300.0
_HEADLINE_LOCK = asyncio.Lock()


def _parse_headlines(xml_bytes, topic):
    if len(xml_bytes) > 2_000_000:
        raise ValueError("Headline feed too large")
    rows = []
    for item in ElementTree.fromstring(xml_bytes).iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        if not title or not link.startswith("https://") or len(link) > 1800:
            continue
        parsed = urlparse(link)
        if parsed.hostname not in {"news.google.com", "news.yahoo.com", "finance.yahoo.com", "www.sec.gov"}:
            continue
        source = (item.findtext("source") or "Google News").strip()[:80]
        published = (item.findtext("pubDate") or "").strip()[:60]
        rows.append({"title": title[:300], "publisher": source, "published_at": published,
                     "url": link, "topic": topic})
        if len(rows) >= 20:
            break
    return rows


@router.get("/headlines")
async def free_headlines(topic: str = Query("politics"), user=Depends(require_scanner)):
    """Free political / Wall Street headlines. No key and no account required."""
    if topic not in HEADLINE_TOPICS:
        raise HTTPException(422, "Unsupported headline topic")
    now = time.monotonic()
    cached = _HEADLINE_CACHE.get(topic)
    if cached and now - cached[0] < _HEADLINE_TTL:
        return {**cached[1], "cached": True}
    async with _HEADLINE_LOCK:
        cached = _HEADLINE_CACHE.get(topic)
        if cached and time.monotonic() - cached[0] < _HEADLINE_TTL:
            return {**cached[1], "cached": True}
        params = {"q": HEADLINE_TOPICS[topic], "hl": "en-US", "gl": "US", "ceid": "US:en"}
        url = "https://news.google.com/rss/search?" + urlencode(params)
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
                response = await client.get(url, headers={"User-Agent": "KAOSTrading-Research/1.0"})
                response.raise_for_status()
                rows = _parse_headlines(response.content, topic)
        except (httpx.HTTPError, ValueError, ElementTree.ParseError) as exc:
            if cached and time.monotonic() - cached[0] < _HEADLINE_TTL * 6:
                return {**cached[1], "cached": True, "stale": True}
            raise HTTPException(503, "Free headline feed unavailable") from exc
        if not rows:
            raise HTTPException(503, "Free headline feed returned no usable articles")
        payload = {"topic": topic, "headlines": rows, "count": len(rows),
                   "provider": "Google News RSS (free, no key)", "research_only": True,
                   "note": "Headlines are discovery links only; timestamps come from the feed, not a verified publisher clock."}
        _HEADLINE_CACHE[topic] = (time.monotonic(), payload)
        return {**payload, "cached": False}


@router.get("/trades")
async def list_disclosures(source: KIND | None=None, ticker: str | None=Query(default=None,max_length=24),
                           limit: int=Query(default=50,ge=1,le=100), user=Depends(require_scanner)):
    query = {}
    if source: query["source"] = source
    if ticker: query["ticker"] = ticker.upper()
    records = await db.kaos_public_disclosures.find(query, {"_id":0}).sort("disclosed_at", -1).limit(limit).to_list(length=limit)
    return {"records": records, "count": len(records), "research_only": True,
            "not_real_time": True, "message": "Reported transactions may be disclosed weeks later; 13F reports show holdings, not executions."}

@router.post("/refresh-sec/{cik}")
async def refresh_sec_form4(cik: int, x_kaos_collector_key: str | None=Header(default=None)):
    """On-demand SEC Form 4 sync. No unattended scheduler or broker actions."""
    from sec_form4_collector import collect_issuer_form4
    key = os.environ.get("KAOS_COLLECTOR_KEY", "")
    if not key or not x_kaos_collector_key or not compare_digest(key, x_kaos_collector_key):
        raise HTTPException(403, "Collector authentication required")
    try:
        docs = await collect_issuer_form4(cik, max_filings=10)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        # Never fabricate records if SEC is unavailable.
        raise HTTPException(503, "SEC Form 4 retrieval unavailable") from exc
    accepted=0
    for doc in docs:
        for row in doc["transactions"]:
            # A transaction is only a classified market purchase/sale if the
            # actual Form 4 XML transaction code supports that interpretation.
            record=Disclosure(
                source="sec_insider", filing_id=doc["filing_id"], filer=row["filer"],
                ticker=row["ticker"], asset=row["asset"], action=row["action"],
                transaction_date=date.fromisoformat(row["transaction_date"]),
                filing_date=date.fromisoformat(doc["filing_date"]),
                disclosed_at=datetime.now(timezone.utc), source_url=doc["source_url"],
                note=("Form " + doc["form"] + "; shares=" + (row["shares"] or "unreported")
                      + "; reported price/share=" + (row["price_per_share"] or "unreported"))
            )
            validate_disclosure(record)
            data=record.model_dump(mode="json")
            await db.kaos_public_disclosures.update_one(
                {"source":"sec_insider","filing_id":data["filing_id"],"filer":data["filer"],
                 "asset":data["asset"],"action":data["action"],"transaction_date":data["transaction_date"]},
                {"$set":data},upsert=True)
            accepted+=1
    return {"filings_examined":len(docs),"transactions_imported":accepted,
            "research_only":True,"automatic_schedule_enabled":False}

@router.post("/sync-sec")
async def sync_latest_sec_filings(ticker: str | None = Query(default=None, max_length=12),
                                 cik: int | None = Query(default=None, ge=1, le=9999999999),
                                 user=Depends(require_scanner)):
    """Member-triggered SEC Form 4 sync.

    Uses SEC's free public data — no key, only the server's declared User-Agent.
    Bounded cooldown per member and issuer so the page can fill itself in without
    hammering sec.gov; SEC asks for at most 10 requests/second industry-wide.
    """
    from sec_form4_collector import collect_issuer_form4
    if not ticker and not cik:
        raise HTTPException(422, "Provide a ticker or a CIK")
    if not os.environ.get("KAOS_SEC_USER_AGENT", ""):
        raise HTTPException(503, "SEC access is not configured; set the SEC User-Agent in Admin → API Keys")
    issuer = cik or await _ticker_to_cik(ticker)
    if not issuer:
        raise HTTPException(404, f"SEC has no issuer with ticker {ticker.upper()}")
    key = (user["id"], issuer)
    now = time.monotonic()
    last = _SEC_SYNC_SEEN.get(key)
    if last and now - last < 300:
        raise HTTPException(429, "That issuer was synced moments ago; try again in a few minutes")
    _SEC_SYNC_SEEN[key] = now
    try:
        docs = await collect_issuer_form4(issuer, max_filings=10)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(503, "SEC Form 4 retrieval unavailable") from exc
    imported = 0
    for doc in docs:
        for row in doc["transactions"]:
            record = Disclosure(
                source="sec_insider", filing_id=doc["filing_id"], filer=row["filer"],
                ticker=row["ticker"], asset=row["asset"], action=row["action"],
                transaction_date=date.fromisoformat(row["transaction_date"]),
                filing_date=date.fromisoformat(doc["filing_date"]),
                disclosed_at=datetime.now(timezone.utc), source_url=doc["source_url"],
                note=("Form " + doc["form"] + "; shares=" + (row["shares"] or "unreported")
                      + "; reported price/share=" + (row["price_per_share"] or "unreported")))
            validate_disclosure(record)
            data = record.model_dump(mode="json")
            await db.kaos_public_disclosures.update_one(
                {"source": "sec_insider", "filing_id": data["filing_id"], "filer": data["filer"],
                 "asset": data["asset"], "action": data["action"], "transaction_date": data["transaction_date"]},
                {"$set": data}, upsert=True)
            imported += 1
    return {"issuer_cik": issuer, "filings_examined": len(docs), "transactions_imported": imported,
            "source": "SEC EDGAR (free)", "research_only": True}


_SEC_SYNC_SEEN: dict = {}
_CIK_CACHE: dict = {"at": 0.0, "map": {}}


async def _ticker_to_cik(ticker: str | None) -> int | None:
    """Resolve a ticker through SEC's free company index (cached for a day)."""
    import httpx
    symbol = (ticker or "").strip().upper()
    if not symbol:
        return None
    if time.monotonic() - _CIK_CACHE["at"] > 86400 or not _CIK_CACHE["map"]:
        agent = os.environ.get("KAOS_SEC_USER_AGENT", "")
        async with httpx.AsyncClient(timeout=20, follow_redirects=False) as client:
            response = await client.get("https://www.sec.gov/files/company_tickers.json",
                                        headers={"User-Agent": agent})
            response.raise_for_status()
            rows = response.json()
        _CIK_CACHE["map"] = {str(r["ticker"]).upper(): int(r["cik_str"]) for r in rows.values()}
        _CIK_CACHE["at"] = time.monotonic()
    return _CIK_CACHE["map"].get(symbol)


@router.post("/refresh-13f/{cik}")
async def refresh_sec_13f(cik: int, x_kaos_collector_key: str | None=Header(default=None)):
    """Refresh publicly filed institutional holdings; never label them as trades."""
    from sec_13f_collector import fetch_13f_holdings
    key=os.environ.get("KAOS_COLLECTOR_KEY","")
    if not key or not x_kaos_collector_key or not compare_digest(key,x_kaos_collector_key):
        raise HTTPException(403,"Collector authentication required")
    try:
        documents=await fetch_13f_holdings(cik,max_filings=5)
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc
    except Exception as exc:
        raise HTTPException(503,"SEC 13F retrieval unavailable") from exc
    accepted=0
    for document in documents:
        for holding in document["holdings"]:
            item=Disclosure(source="institutional_13f",filing_id=document["filing_id"],
                filer=f"SEC institutional filer CIK {cik}",
                asset=holding["issuer"]+" (CUSIP "+holding["cusip"]+")",
                ticker=None,action="holding",transaction_date=None,
                filing_date=date.fromisoformat(document["filing_date"]),
                disclosed_at=datetime.now(timezone.utc),source_url=document["source_url"],
                note=("Form "+document["form"]+"; reported value (USD thousands): "
                      +holding["reported_value_thousands_usd"]+
                      "; shares/principal: "+str(holding["reported_shares_or_principal"] or "not specified")))
            validate_disclosure(item)
            record=item.model_dump(mode="json")
            await db.kaos_public_disclosures.update_one(
              {"source":record["source"],"filing_id":record["filing_id"],"filer":record["filer"],
               "asset":record["asset"],"action":"holding","transaction_date":None},
              {"$set":record},upsert=True)
            accepted+=1
    return {"filings_examined":len(documents),"holdings_imported":accepted,
            "research_only":True,"automatic_schedule_enabled":False,
            "warning":"13F shows quarterly holdings, not the date of buying or selling."}

@router.post("/compare-13f/{cik}")
async def compare_13f_quarters(cik: int, x_kaos_collector_key: str | None=Header(default=None)):
    """Compare two official filings; net changes are not verified executions."""
    from sec_13f_collector import fetch_13f_holdings
    from sec_13f_comparison import compare_holdings
    key=os.environ.get("KAOS_COLLECTOR_KEY","")
    if not key or not x_kaos_collector_key or not compare_digest(key,x_kaos_collector_key):
        raise HTTPException(403,"Collector authentication required")
    try:
        docs=await fetch_13f_holdings(cik,max_filings=5)
        if len(docs)<2:
            return {"cik":cik,"comparison_available":False,"changes":[],"reason":"Two verified filings needed"}
        latest,previous=docs[0],docs[1]
        changes=compare_holdings(previous["holdings"],latest["holdings"])
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc
    except Exception as exc:
        raise HTTPException(503,"SEC holdings comparison unavailable") from exc
    record={"cik":cik,"previous_filing_id":previous["filing_id"],
            "latest_filing_id":latest["filing_id"],
            "previous_filing_date":previous["filing_date"],"latest_filing_date":latest["filing_date"],
            "previous_source_url":previous["source_url"],"latest_source_url":latest["source_url"],
            "changes":changes,"calculated_at":datetime.now(timezone.utc).isoformat()}
    await db.kaos_13f_comparisons.update_one(
        {"cik":cik,"latest_filing_id":latest["filing_id"],
         "previous_filing_id":previous["filing_id"]},{"$set":record},upsert=True)
    return {"comparison_available":True,"research_only":True,"not_executed_trades":True,**record}

@router.get("/institutional-changes")
async def institutional_changes(cik: int=Query(ge=1,le=9999999999),
                                user=Depends(require_scanner)):
    row=await db.kaos_13f_comparisons.find_one({"cik":cik},{"_id":0},sort=[("calculated_at",-1)])
    return {"comparison_available":bool(row),"research_only":True,
            "not_executed_trades":True,"data":row}
