"""Cookie mutation CSRF controls: no Origin bypass, bearer remains usable."""
from types import SimpleNamespace
import pytest
import asyncio
from fastapi import HTTPException
import auth

def req(method, origin=None, referer=None):
    h={}
    if origin is not None: h["origin"]=origin
    if referer is not None: h["referer"]=referer
    return SimpleNamespace(method=method,headers=h)

@pytest.mark.parametrize("origin", [None,"null","https://attacker.example","https://tradingwithkaos.com.evil.test"])
def test_rejects_untrusted_cookie_write_origins(monkeypatch,origin):
    monkeypatch.setenv("FRONTEND_URL","https://tradingwithkaos.com")
    monkeypatch.setenv("KAOS_ENV","production")
    assert not auth._cookie_write_origin_allowed(req("POST",origin))

def test_allows_matching_frontend_origin(monkeypatch):
    monkeypatch.setenv("FRONTEND_URL","https://tradingwithkaos.com")
    assert auth._cookie_write_origin_allowed(req("PATCH","https://tradingwithkaos.com"))

def test_get_remains_safe_without_origin():
    assert auth._cookie_write_origin_allowed(req("GET"))

def test_matching_referer_fallback(monkeypatch):
    monkeypatch.setenv("FRONTEND_URL","https://tradingwithkaos.com")
    assert auth._cookie_write_origin_allowed(req("DELETE",referer="https://tradingwithkaos.com/account"))

def test_cookie_write_rejected_before_token_lookup(monkeypatch):
    request=SimpleNamespace(method="POST",headers={},cookies={"access_token":"ambient"})
    with pytest.raises(HTTPException) as exc:
        asyncio.run(auth.get_current_user(request))
    assert exc.value.status_code==403
