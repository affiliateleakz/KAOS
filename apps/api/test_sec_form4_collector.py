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

def test_rendered_primary_document_resolves_to_raw_xml(monkeypatch):
    """submissions.json reports the HTML-rendered copy; the XML lives at the filing root."""
    monkeypatch.setenv("KAOS_SEC_USER_AGENT","KAOS Trading support@tradewithkaos.com")
    payload={"filings":{"recent":{"form":["4"],
      "accessionNumber":["0001140361-26-043484"],
      "primaryDocument":["xslF345X06/form4.xml"],
      "filingDate":["2026-11-12"]}}}
    calls=[]
    async def get(url,**kwargs):
        calls.append(url)
        return Response(payload) if url.endswith(".json") else Response(None)
    client=type("Client",(),{})()
    client.get=get
    result=asyncio.run(collect_issuer_form4(320193,client=client))
    assert len(result)==1
    expected="https://www.sec.gov/Archives/edgar/data/320193/000114036126043484/form4.xml"
    assert calls[1]==expected
    assert result[0]["source_url"]==expected

def test_non_xml_primary_document_never_fetched(monkeypatch):
    monkeypatch.setenv("KAOS_SEC_USER_AGENT","KAOS Trading support@tradewithkaos.com")
    payload={"filings":{"recent":{"form":["4"],
      "accessionNumber":["0001140361-26-043484"],
      "primaryDocument":["../../etc/passwd"],
      "filingDate":["2026-11-12"]}}}
    client=type("Client",(),{})()
    client.get=AsyncMock(side_effect=[Response(payload)])
    result=asyncio.run(collect_issuer_form4(320193,client=client))
    assert result==[]
    assert client.get.await_count==1
