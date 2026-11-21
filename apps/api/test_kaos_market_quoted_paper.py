"""Server-derived crypto paper-quote safety boundary regression tests."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest
import routes_paper as paper
from market_data import Quote, QuoteUnavailable

NOW=datetime.now(timezone.utc)

def quote(time=None):
    return Quote(symbol="BTC-USD",bid=Decimal("69999"),ask=Decimal("70001"),
                 last=Decimal("70000"),quote_time=time or NOW,
                 fetched_at=NOW,source="coinbase_exchange_public_ticker")

@pytest.mark.asyncio
async def test_market_paper_uses_server_ask_not_client_price(monkeypatch):
    observed={}
    async def fake_quote(symbol, asset):
        observed["requested"]=(symbol,asset)
        return quote()
    async def fake_submit(user,symbol,asset_class,side,quantity,price,cid,**kwargs):
        observed.update(symbol=symbol,side=side,quantity=quantity,price=price,
                        market_quote=kwargs["market_quote"])
        return {"state":"SUBMITTED","paper":True}
    monkeypatch.setattr(paper,"get_quote",fake_quote)
    monkeypatch.setattr(paper,"_submit",fake_submit)
    req=paper.MarketPaperOrderReq(symbol="btc-usd",side="BUY",quantity="5")
    out=await paper.place_market_derived_paper_order(req,user={"id":"owner"})
    assert out["paper"]
    assert observed["requested"]==("BTC-USD","CRYPTO_SPOT")
    assert observed["price"]=="70001"
    assert observed["market_quote"].source=="coinbase_exchange_public_ticker"

@pytest.mark.asyncio
async def test_market_paper_uses_server_bid_to_sell(monkeypatch):
    prices=[]
    async def fake_quote(*args):return quote()
    async def fake_submit(*args,**kwargs):
        prices.append(args[5])
        return {"paper":True}
    monkeypatch.setattr(paper,"get_quote",fake_quote)
    monkeypatch.setattr(paper,"_submit",fake_submit)
    req=paper.MarketPaperOrderReq(symbol="BTC-USD",side="SELL",quantity="5")
    await paper.place_market_derived_paper_order(req,user={"id":"owner"})
    assert prices==["69999"]

@pytest.mark.asyncio
async def test_market_paper_rejects_stale_quote(monkeypatch):
    async def stale(*args):return quote(NOW-timedelta(minutes=5))
    monkeypatch.setattr(paper,"get_quote",stale)
    req=paper.MarketPaperOrderReq(symbol="BTC-USD",quantity="5")
    with pytest.raises(paper.HTTPException) as info:
        await paper.place_market_derived_paper_order(req,user={"id":"owner"})
    assert info.value.status_code==503

@pytest.mark.asyncio
async def test_market_paper_fails_if_source_unavailable(monkeypatch):
    async def unavailable(*args):
        raise QuoteUnavailable("Provider unavailable")
    monkeypatch.setattr(paper,"get_quote",unavailable)
    req=paper.MarketPaperOrderReq(symbol="BTC-USD",quantity="5")
    with pytest.raises(paper.HTTPException) as info:
        await paper.place_market_derived_paper_order(req,user={"id":"owner"})
    assert info.value.status_code==503

def test_only_supported_crypto_market_accepted():
    with pytest.raises(Exception):
        paper.MarketPaperOrderReq(symbol="SPY",asset_class="EQUITY",quantity="5")
