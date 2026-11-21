"""Alpaca PAPER market quote and manual order boundary tests.

Tests use no live credentials and make no external HTTP requests.
"""
import asyncio
from datetime import datetime,timedelta,timezone
from decimal import Decimal
import pytest

from alpaca_paper_quotes import parse_stock_quote, MarketUnavailable
from alpaca_paper_client import submit_stock_paper_buy, lookup_paper_order, AlpacaPaperUnavailable
import alpaca_paper_client
import routes_alpaca_paper_orders as order

NOW=datetime(2026,11,20,17,0,tzinfo=timezone.utc)


def ticker(timestamp=None, bid=100, ask=100.03):
    return {"symbol":"AAPL","quote":{
        "bp":bid,"ap":ask,"t":(timestamp or NOW).isoformat().replace("+00:00","Z")
    }}


def test_recent_alpaca_iex_quote():
    q=parse_stock_quote("AAPL",ticker(),now=NOW+timedelta(seconds=4))
    assert q["source"]=="alpaca_stock_iex"
    assert q["ask"]=="100.03"
    assert q["age_seconds"]==4


def test_stale_or_future_iex_quote_rejected():
    with pytest.raises(MarketUnavailable):
        parse_stock_quote("AAPL",ticker(),now=NOW+timedelta(seconds=11))
    with pytest.raises(MarketUnavailable):
        parse_stock_quote("AAPL",ticker(NOW+timedelta(seconds=1)),now=NOW)
    with pytest.raises(MarketUnavailable):
        parse_stock_quote("MSFT",ticker(),now=NOW)


def test_invalid_quote_rejected():
    with pytest.raises(MarketUnavailable):
        parse_stock_quote("AAPL",ticker(bid=101,ask=100),now=NOW)
    with pytest.raises(MarketUnavailable):
        parse_stock_quote("AAPL",ticker(bid=-1),now=NOW)


def test_broker_paper_submit_payload_and_fixed_method(monkeypatch):
    calls=[]
    async def request(key,secret,method,path,*,payload=None):
        calls.append((method,path,payload))
        return {"client_order_id":payload["client_order_id"],"status":"accepted"}
    monkeypatch.setattr(alpaca_paper_client,"paper_request",request)
    cid="kaos-paper-"+"a"*32
    result=asyncio.run(submit_stock_paper_buy("paperkey12345","papersecret12345",
        symbol="AAPL",notional="10",client_order_id=cid))
    assert result["status"]=="accepted"
    assert calls[0]==("POST","/v2/orders",{
        "symbol":"AAPL","notional":"10","side":"buy","type":"market",
        "time_in_force":"day","client_order_id":cid
    })
    with pytest.raises(AlpacaPaperUnavailable):
        asyncio.run(submit_stock_paper_buy("key","secret",symbol="BTC/USD",
            notional="10",client_order_id=cid))


def test_order_notional_and_instrument_restriction():
    for value in ("0","-1","26","NaN","Infinity","0.01"):
        with pytest.raises(order.HTTPException):
            order._notional(value)
    assert order._notional("25")==Decimal("25")
    assert not order.SYMBOL.fullmatch("BTC/USD")
    assert not order.SYMBOL.fullmatch("SPY241220C00500000")


def test_owner_feature_flag_default_off(monkeypatch):
    monkeypatch.delenv("KAOS_ALPACA_PAPER_ORDERS_ENABLED",raising=False)
    with pytest.raises(order.HTTPException) as error:
        asyncio.run(order.guard({"id":"owner","role":"admin"}))
    assert error.value.status_code==503


def test_stale_qualitative_ai_cannot_be_converted_to_order():
    # The manual gateway only accepts ticker/notional and a one-use preview;
    # it has no signal_id, prediction, broker URL, or live key arguments.
    assert set(order.PreviewReq.model_fields)=={"symbol","notional"}
    assert set(order.ConfirmReq.model_fields)=={"preview_id"}


def test_invalid_candle_timeframe_refused_before_market_request():
    from alpaca_paper_quotes import stock_candles
    with pytest.raises(MarketUnavailable):
        asyncio.run(stock_candles("key","secret","AAPL",seconds=5))
    with pytest.raises(MarketUnavailable):
        asyncio.run(stock_candles("key","secret","SPY/US",seconds=60))
