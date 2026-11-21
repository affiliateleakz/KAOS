"""Alpaca paper connection must never silently route to a live account."""
import asyncio
import pytest
from alpaca_paper_client import (
    PAPER_ORIGIN, AlpacaPaperUnavailable, paper_request,
    verify_paper_account, paper_account, paper_positions, paper_orders,
)

class FakeResponse:
    def __init__(self, body, status=200):
        self.body=body
        self.status_code=status
        self.content=b"{}"
    def json(self):return self.body

def install(monkeypatch, responses):
    calls=[]
    class Client:
        def __init__(self,**kwargs):
            assert kwargs.get("follow_redirects") is False
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def request(self,method,url,headers=None,json=None):
            calls.append((method,url,headers))
            return responses.pop(0)
    monkeypatch.setattr("alpaca_paper_client.httpx.AsyncClient",Client)
    return calls

def test_verify_uses_only_paper_hostname(monkeypatch):
    calls=install(monkeypatch,[FakeResponse({"id":"paper-account-123456",
                                               "status":"ACTIVE","trading_blocked":False})])
    out=asyncio.run(verify_paper_account("paperkey1234567","papersecret12345678"))
    assert out["status"]=="ACTIVE"
    assert calls[0][1]==PAPER_ORIGIN+"/v2/account"
    assert calls[0][2]["APCA-API-KEY-ID"]=="paperkey1234567"

def test_no_arbitrary_url_or_redirect(monkeypatch):
    calls=install(monkeypatch,[FakeResponse({},302)])
    with pytest.raises(AlpacaPaperUnavailable):
        asyncio.run(paper_request("paperkey1234567","papersecret12345678","GET","/v2/account"))
    with pytest.raises(AlpacaPaperUnavailable):
        asyncio.run(paper_request("paperkey1234567","papersecret12345678","GET","https://api.alpaca.markets/v2/account"))
    with pytest.raises(AlpacaPaperUnavailable):
        asyncio.run(paper_request("paperkey1234567","papersecret12345678","PUT","/v2/account"))
    assert len(calls)==1

def test_portfolio_outputs_do_not_include_secrets(monkeypatch):
    calls=install(monkeypatch,[
        FakeResponse({"status":"ACTIVE","cash":"100000","equity":"100123",
                      "buying_power":"200000","secret_key":"wrong"}),
        FakeResponse([{"symbol":"AAPL","qty":"3","unrealized_pl":"12","token":"do not return"}]),
        FakeResponse([{"id":"order1","symbol":"AAPL","side":"buy","status":"filled",
                       "filled_qty":"3","private_note":"do not return"}]),
    ])
    key,secret="paperkey1234567","papersecret12345678"
    acct=asyncio.run(paper_account(key,secret))
    positions=asyncio.run(paper_positions(key,secret))
    orders=asyncio.run(paper_orders(key,secret))
    assert "secret_key" not in acct
    assert "token" not in positions[0]
    assert "private_note" not in orders[0]
    assert all(call[1].startswith(PAPER_ORIGIN+"/v2/") for call in calls)
