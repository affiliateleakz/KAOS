import pytest
from sec_form4_parser import parse_form4

XML = """<ownershipDocument>
<issuer><issuerName>Example Inc</issuerName><issuerTradingSymbol>EXMP</issuerTradingSymbol></issuer>
<reportingOwner><reportingOwnerId><rptOwnerName>Sample Officer</rptOwnerName></reportingOwnerId></reportingOwner>
<nonDerivativeTable><nonDerivativeTransaction><transactionDate><value>2026-10-01</value></transactionDate>
<transactionCoding><transactionCode>P</transactionCode></transactionCoding>
<transactionAmounts><transactionShares><value>100</value></transactionShares>
<transactionPricePerShare><value>20.50</value></transactionPricePerShare>
<transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode>
</transactionAmounts></nonDerivativeTransaction></nonDerivativeTable></ownershipDocument>"""

def test_parse_reported_purchase():
    rows=parse_form4(XML)
    assert len(rows)==1 and rows[0]["action"]=="buy"
    assert rows[0]["transaction_date"]=="2026-10-01"
    assert rows[0]["ticker"]=="EXMP"

def test_reject_doctype():
    with pytest.raises(ValueError,match="Unsafe"):
        parse_form4("<!DOCTYPE foo>"+XML)

def test_refuse_unknown_document():
    with pytest.raises(ValueError):
        parse_form4("<notAnOwnershipReport/>")
