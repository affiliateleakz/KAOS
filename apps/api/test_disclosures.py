import asyncio
from datetime import datetime,timezone,date
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
import routes_disclosures as scanner

def item(**change):
    base=dict(source="senate",filing_id="PTR-2026-123",filer="Public Official",
      ticker="AAPL",asset="Apple Inc",action="buy",transaction_date=date(2026,9,1),
      filing_date=date(2026,10,1),disclosed_at=datetime(2026,10,1,tzinfo=timezone.utc),
      source_url="https://efdsearch.senate.gov/search/home/")
    base.update(change)
    return scanner.Disclosure(**base)

def test_reject_fake_filing_source():
    with pytest.raises(ValueError,match="Official"):
        scanner.validate_disclosure(item(source_url="https://not-official.example/filing"))

def test_reject_13f_fake_trade():
    with pytest.raises(ValueError,match="13F"):
        scanner.validate_disclosure(item(source="institutional_13f",action="buy",transaction_date=None,
                                         source_url="https://www.sec.gov/Archives/edgar/data/1/filing"))

def test_13f_holding_allowed():
    scanner.validate_disclosure(item(source="institutional_13f",action="holding",transaction_date=None,
                                     source_url="https://www.sec.gov/Archives/edgar/data/1/filing"))

def test_ingest_requires_collector_auth(monkeypatch):
    monkeypatch.setenv("KAOS_COLLECTOR_KEY","secret")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(scanner.ingest_disclosures([item()],x_kaos_collector_key="wrong"))
    assert exc.value.status_code==403

def test_member_access_checks_entitlement(monkeypatch):
    monkeypatch.setattr(scanner,"get_entitlements",AsyncMock(return_value={"scanners":False}))
    with pytest.raises(HTTPException) as exc:
        asyncio.run(scanner.require_scanner(user={"id":"member"}))
    assert exc.value.status_code==403

def test_house_disclosures_require_commercial_review(monkeypatch):
    monkeypatch.delenv("KAOS_HOUSE_DISCLOSURE_RIGHTS",raising=False)
    with pytest.raises(ValueError,match="commercial-use"):
        scanner.validate_disclosure(item(source="house",source_url="https://disclosures-clerk.house.gov/FinancialDisclosure"))

def test_reject_source_mismatch():
    with pytest.raises(ValueError,match="category"):
        scanner.validate_disclosure(item(source="senate",source_url="https://www.sec.gov/Archives/edgar/data/1"))
