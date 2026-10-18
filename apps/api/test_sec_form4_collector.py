import asyncio
from unittest.mock import AsyncMock
import pytest
from sec_form4_collector import collect_issuer_form4

class Response:
    def __init__(self,payload):self.payload=payload
    def raise_for_status(self):pass
    def json(self):return self.payload
    @property
    def text(self):return "<ownershipDocument><issuer><issuerTradingSymbol>X</issuerTradingSymbol></issuer><reportingOwner><reportingOwnerId><rptOwnerName>Person</rptOwnerName></reportingOwnerId></reportingOwner></ownershipDocument>"

def test_identified_user_agent_required(monkeypatch):
    monkeypatch.delenv("KAOS_SEC_USER_AGENT",raising=False)
    with pytest.raises(RuntimeError,match="User-Agent"):
        asyncio.run(collect_issuer_form4(123456,client=object()))

def test_reject_cik():
    with pytest.raises(ValueError):asyncio.run(collect_issuer_form4(-1))

def test_only_form4_metadata_fetched(monkeypatch):
    monkeypatch.setenv("KAOS_SEC_USER_AGENT","KAOS Trading support@tradewithkaos.com")
    payload={"filings":{"recent":{"form":["4","10-K","4"],
      "accessionNumber":["0000123456-26-000001","0000123456-26-000002","0000123456-26-000003"],
      "primaryDocument":["ownership.xml","report.htm","other.htm"],
      "filingDate":["2026-10-01","2026-10-02","2026-10-03"]}}}
    client=type("Client",(),{})()
    client.get=AsyncMock(side_effect=[Response(payload),Response(None)])
    result=asyncio.run(collect_issuer_form4(123456,client=client))
    assert len(result)==1 and result[0]["filing_id"]=="0000123456-26-000001"
    assert client.get.await_count==2
