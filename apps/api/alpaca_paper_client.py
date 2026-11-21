"""Strict Alpaca PAPER-only HTTP client.

Never accepts a configurable base URL, never makes requests to the live
Alpaca trading hostname. Key/secret come from KAOS encrypted broker vault.
"""
from urllib.parse import quote
import httpx

PAPER_ORIGIN = "https://paper-api.alpaca.markets"
HEADERS = ("APCA-API-KEY-ID", "APCA-API-SECRET-KEY")


class AlpacaPaperUnavailable(Exception):
    pass


def _check_credentials(key, secret):
    if not isinstance(key,str) or not isinstance(secret,str):
        raise AlpacaPaperUnavailable("Invalid paper key")
    if not 8 <= len(key.strip()) <= 512 or not 16 <= len(secret.strip()) <= 2048:
        raise AlpacaPaperUnavailable("Invalid paper key")
    return {HEADERS[0]:key.strip(),HEADERS[1]:secret.strip()}


async def paper_request(key, secret, method, path, *, payload=None):
    if method not in ("GET","POST","DELETE") or not path.startswith("/v2/"):
        raise AlpacaPaperUnavailable("Unsupported paper API operation")
    if "://" in path or "?" in path or ".." in path or "//" in path:
        raise AlpacaPaperUnavailable("Unsafe paper API path")
    headers=_check_credentials(key,secret)
    try:
        async with httpx.AsyncClient(timeout=12,follow_redirects=False) as client:
            response=await client.request(
                method,PAPER_ORIGIN+path,
                headers=headers,
                json=payload)
    except httpx.HTTPError as exc:
        raise AlpacaPaperUnavailable("Alpaca paper API unavailable") from exc
    if response.status_code in (301,302,303,307,308):
        raise AlpacaPaperUnavailable("Alpaca paper API redirected unexpectedly")
    if response.status_code in (401,403):
        raise AlpacaPaperUnavailable("Alpaca rejected paper account credentials or permissions")
    if response.status_code >= 400:
        raise AlpacaPaperUnavailable("Alpaca paper request rejected by broker")
    try:
        return response.json() if response.content else {}
    except ValueError as exc:
        raise AlpacaPaperUnavailable("Alpaca paper response was invalid") from exc


async def verify_paper_account(key, secret):
    data=await paper_request(key,secret,"GET","/v2/account")
    if not isinstance(data,dict) or not data.get("id") or not data.get("status"):
        raise AlpacaPaperUnavailable("No verified Alpaca paper account")
    return {"status":data["status"],
            "account_id_hint":"…"+str(data["id"])[-4:],
            "trading_blocked":bool(data.get("trading_blocked",False))}


async def paper_account(key, secret):
    data=await paper_request(key,secret,"GET","/v2/account")
    return {
        "status":data.get("status"),
        "cash":data.get("cash"),"equity":data.get("equity"),
        "buying_power":data.get("buying_power"),
        "portfolio_value":data.get("portfolio_value"),
        "trading_blocked":data.get("trading_blocked"),
        "paper":True
    }


async def paper_positions(key, secret):
    data=await paper_request(key,secret,"GET","/v2/positions")
    if not isinstance(data,list):
        raise AlpacaPaperUnavailable("Unexpected position list")
    fields=("symbol","asset_class","qty","avg_entry_price","market_value",
            "unrealized_pl","current_price","side")
    return [{k:r.get(k) for k in fields} for r in data[:100] if isinstance(r,dict)]


async def paper_orders(key, secret):
    # Explicitly whitelist only this constant list operation
    data=await paper_request(key,secret,"GET","/v2/orders")
    if not isinstance(data,list):
        raise AlpacaPaperUnavailable("Unexpected order list")
    fields=("id","client_order_id","symbol","asset_class","side","type",
            "status","qty","notional","filled_qty","filled_avg_price","created_at")
    return [{k:r.get(k) for k in fields} for r in data[:100] if isinstance(r,dict)]
