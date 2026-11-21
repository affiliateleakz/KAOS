"""Alpaca paper fill pagination and accounting-integrity tests (offline)."""
import asyncio
from datetime import datetime,timezone
import pytest
import alpaca_paper_fill_audit as audit
from alpaca_paper_client import AlpacaPaperUnavailable, PAPER_ORIGIN

STAMP="2026-11-20T18:05:12Z"

def fill(i,*,order_id="alpaca-order-1",side="buy",qty="0.5",price="100"):
    return {"activity_type":"FILL","id":f"activity-{i:04d}",
        "order_id":order_id,"symbol":"AAPL","side":side,
        "qty":qty,"price":price,"transaction_time":STAMP}

def fake_client(monkeypatch,pages):
    calls=[]
    class Response:
        status_code=200
        def __init__(self,page): self.page=page
        def json(self): return self.page
    class Client:
        def __init__(self,**kwargs):
            assert kwargs.get("follow_redirects") is False
        async def __aenter__(self): return self
        async def __aexit__(self,*args): return False
        async def get(self,url,params=None,headers=None):
            calls.append((url,dict(params),headers))
            return Response(pages.pop(0))
    monkeypatch.setattr(audit.httpx,"AsyncClient",Client)
    return calls

def test_no_fill_history_is_not_pnl(monkeypatch):
    calls=fake_client(monkeypatch,[[]])
    result=asyncio.run(audit.fetch_broker_fills("paperkey1234567","papersecret12345678"))
    assert result["fills"]==[]
    assert result["partial_history"] is False
    assert calls[0][0]==PAPER_ORIGIN+"/v2/account/activities/FILL"

def test_paginated_history_uses_source_last_id_cursor(monkeypatch):
    a=[fill(i) for i in range(100)]
    b=[fill(100),fill(101)]
    calls=fake_client(monkeypatch,[a,b])
    result=asyncio.run(audit.fetch_broker_fills("paperkey1234567","papersecret12345678"))
    assert result["records_returned"]==102
    assert result["partial_history"] is False
    assert calls[1][1]["page_token"]=="activity-0099"

def test_bounded_history_not_called_complete(monkeypatch):
    fake_client(monkeypatch,[[fill(i) for i in range(100)]])
    result=asyncio.run(audit.fetch_broker_fills("paperkey1234567","papersecret12345678",max_pages=1))
    assert result["partial_history"] is True

def test_bad_activity_ignored_and_disclosed(monkeypatch):
    fake_client(monkeypatch,[[fill(1),{**fill(2),"price":"nan"}]])
    result=asyncio.run(audit.fetch_broker_fills("paperkey1234567","papersecret12345678"))
    assert result["rejected_records"]==1
    assert result["records_returned"]==1

def test_reconcile_known_order_without_claiming_profit():
    response={"fills":[fill(1),fill(2,qty="0.25",price="110"),
                       fill(3,order_id="unrecognized")],
              "partial_history":False,"rejected_records":0}
    order={"client_order_id":"kaos-paper-abc","broker_id":"alpaca-order-1",
           "symbol":"AAPL","broker":"alpaca_paper"}
    result=audit.reconcile_kaos_fills(response,[order])
    assert result["matched_orders"]==1
    assert result["matched_fills"]==2
    assert result["rows"][0]["filled_qty"]=="0.75"
    assert result["rows"][0]["gross_buy_notional"]=="77.50"
    assert result["unmatched_broker_fills"]==1
    assert result["realized_pnl_verified"] is False
    assert result["rows"][0]["realized_pnl"] is None
    assert result["daily_loss_limit_verified"] is False
    assert result["auto_paper_execution_enabled"] is False

@pytest.mark.parametrize("field,value",[
    ("qty","0"),("price","-2"),("price","Infinity"),
    ("transaction_time","yesterday"),("side","unknown"),
])
def test_invalid_fill_is_never_counted(field,value):
    row=fill(1);row[field]=value
    with pytest.raises(ValueError):
        audit.normalize_fill(row)
