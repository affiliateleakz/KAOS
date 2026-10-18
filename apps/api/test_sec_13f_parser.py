import pytest
from sec_13f_parser import parse_13f_information_table

XML='''<informationTable xmlns="http://www.sec.gov/edgar/document/thirteenf/informationtable">
<infoTable><nameOfIssuer>Example Company</nameOfIssuer><titleOfClass>COM</titleOfClass>
<cusip>123456789</cusip><value>2500</value>
<shrsOrPrnAmt><sshPrnamt>10000</sshPrnamt><sshPrnamtType>SH</sshPrnamtType></shrsOrPrnAmt>
</infoTable></informationTable>'''

def test_13f_yields_holdings_not_trades():
    rows=parse_13f_information_table(XML)
    assert len(rows)==1
    assert rows[0]["action"]=="holding"
    assert rows[0]["ticker"] is None
    assert rows[0]["reported_value_thousands_usd"]=="2500"
    assert rows[0]["reported_shares_or_principal"]=="10000"

def test_disallow_external_entities():
    with pytest.raises(ValueError,match="Unsafe"):
        parse_13f_information_table("<!DOCTYPE root>"+XML)

def test_disallow_non_13f_document():
    with pytest.raises(ValueError,match="Not a 13F"):
        parse_13f_information_table("<portfolio/>")
