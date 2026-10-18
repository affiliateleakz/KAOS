import asyncio
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
import routes_crypto_scanner as scanner

def test_normalize_pair_metrics():
    p={"chainId":"solana","dexId":"raydium","pairAddress":"abc",
       "url":"https://dexscreener.com/solana/abc",
       "baseToken":{"symbol":"SOL","name":"Solana"},
       "liquidity":{"usd":50000},"volume":{"h24":125000},
       "priceChange":{"h24":-6.5},"priceUsd":"145.2",
       "txns":{"h24":{"buys":50,"sells":37}}}
    card=scanner.pair_card(p)
    assert card["change_24h"]==-6.5 and card["liquidity_usd"]==50000
    assert card["verified_safe"] is False

def test_nonfinite_price_not_exposed():
    assert scanner.numeric("NaN") is None
    assert scanner.numeric("Infinity") is None

def test_invalid_query_rejected(monkeypatch):
    with pytest.raises(HTTPException) as exc:
        asyncio.run(scanner.find_crypto_pairs(q="https://unsafe.example/a",user={"id":"member"}))
    assert exc.value.status_code==422

def test_market_search_returns_read_only(monkeypatch):
    monkeypatch.setattr(scanner,"dex_get",AsyncMock(return_value={"pairs":[]}))
    result=asyncio.run(scanner.find_crypto_pairs(q="SOL",user={"id":"member"}))
    assert result["trade_execution_enabled"] is False
    assert result["pairs"]==[]
