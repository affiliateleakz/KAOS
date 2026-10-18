from datetime import datetime,timezone
from decimal import Decimal
import pytest
from market_data import parse_coinbase_ticker, QuoteUnavailable, closed_candles

def test_quote_and_provenance():
    now=datetime.now(timezone.utc)
    q=parse_coinbase_ticker("BTC-USD",{"bid":"10","ask":"11","price":"10.5","time":"2026-10-18T12:00:00.123456789Z"},now)
    assert q.bid==Decimal("10")
    assert q.provenance()["source"]=="coinbase_exchange_public_ticker"

@pytest.mark.parametrize("bid,ask", [("NaN","11"),("12","11"),("0","11")])
def test_invalid_quote_rejected(bid,ask):
    with pytest.raises(QuoteUnavailable):
        parse_coinbase_ticker("BTC-USD",{"bid":bid,"ask":ask,"price":"10","time":"2026-10-18T12:00:00Z"},datetime.now(timezone.utc))

def test_forming_candle_excluded():
    t=1800000120
    rows=[[1800000100,1,3,2,2,8],[1800000000,1,3,2,2,8]]
    assert [x["time"] for x in closed_candles(rows,60,datetime.fromtimestamp(t,timezone.utc))]==[1800000000]
