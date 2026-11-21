"""Paper-only order API on top of DurablePaperPipeline. Never routes to a live broker.

The quote price is caller-supplied until an authorized market-data feed exists,
so results are simulation records only.
"""
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth import get_current_user, require_role
from db import db
from services import get_setting, set_setting, audit_log
from kaos_broker_core import OrderIntent, AssetClass, OrderKind
from kaos_broker_registry import BrokerRegistry, BrokerUnavailable
from kaos_paper_adapter import PaperAdapter
from kaos_paper_journal import PaperOrderJournal
from kaos_risk_engine import RiskLimits, RiskSnapshot, RiskRejected
from kaos_durable_paper_pipeline import DurablePaperPipeline
from kaos_paper_book import base_units, build_book, book_view, money
from market_data import get_quote, QuoteUnavailable

router = APIRouter(prefix="/api/v1/paper", tags=["paper-trading"])
admin_dep = require_role("admin")

PAPER_ACCOUNT = "paper-default"
PAPER_STARTING_BALANCE = Decimal("100")

_registry = BrokerRegistry()
_registry.register(PaperAdapter(), enabled=True, paper_only=True)
_pipeline = DurablePaperPipeline(
    _registry, RiskLimits(), PaperOrderJournal(os.environ.get("KAOS_PAPER_JOURNAL_PATH", "/tmp/kaos_paper_journal.db")))


class PaperOrderReq(BaseModel):
    symbol: str = Field(min_length=1, max_length=30)
    asset_class: Literal["CRYPTO_SPOT", "FOREX", "EQUITY"] = "CRYPTO_SPOT"
    side: Literal["BUY", "SELL"] = "BUY"
    quantity: str = Field(description="Quote-currency notional, e.g. '10' = $10")
    quote_price: str
    client_order_id: Optional[str] = Field(default=None, max_length=64)


class MarketPaperOrderReq(BaseModel):
    symbol: str = Field(min_length=3, max_length=30)
    asset_class: Literal['CRYPTO_SPOT'] = 'CRYPTO_SPOT'
    side: Literal['BUY','SELL'] = 'BUY'
    quantity: str = Field(description='USD notional, capped by paper risk limits')
    client_order_id: Optional[str] = Field(default=None,max_length=64)


class ClosePositionReq(BaseModel):
    quote_price: str
    client_order_id: Optional[str] = Field(default=None, max_length=64)


class KillSwitchReq(BaseModel):
    active: bool


def build_snapshot(book, quote_price, now, emergency_stopped, quote_timestamp=None):
    """Risk snapshot from the user's simulated paper book."""
    return RiskSnapshot(
        now=now, quote_timestamp=quote_timestamp or now, quote_price=quote_price, daily_realized_pnl=str(book["realized_today"]),
        open_exposure=str(book["open_cost"]), open_positions=len(book["open"]),
        available_quote_balance=str(max(book["cash"], Decimal("0"))),
        emergency_stopped=emergency_stopped)


async def kill_switch_active():
    return bool(await get_setting("paper_kill_switch", False))


async def _user_book(user, now):
    history = await db.paper_orders.find({"user_id": user["id"]}, {"_id": 0}).to_list(5000)
    return build_book(history, PAPER_STARTING_BALANCE, today=now.date().isoformat())


def _positive(value, label):
    try:
        d = Decimal(str(value))
    except InvalidOperation:
        raise HTTPException(status_code=422, detail=f"Paper order rejected: invalid {label}")
    if not d.is_finite() or d <= 0:
        raise HTTPException(status_code=422, detail=f"Paper order rejected: invalid {label}")
    return d


async def _reject(user, now, client_order_id, symbol, side, quantity, quote_price, reason):
    await db.paper_order_rejections.insert_one({
        "user_id": user["id"], "client_order_id": client_order_id, "symbol": symbol,
        "side": side, "quantity": quantity, "quote_price": quote_price,
        "state": "REJECTED", "reason": reason, "paper": True, "created_at": now.isoformat()})
    raise HTTPException(status_code=422, detail=f"Paper order rejected: {reason}")


async def _submit(user, symbol, asset_class, side, quantity, quote_price, client_order_id, *, close_all=False, market_quote=None):
    now = datetime.now(timezone.utc)
    symbol = symbol.upper()
    client_order_id = client_order_id or f"web-{uuid.uuid4().hex[:16]}"
    key = {"user_id": user["id"], "client_order_id": client_order_id}
    existing = await db.paper_orders.find_one(key, {"_id": 0})
    price = _positive(quote_price, "quote price")
    book = await _user_book(user, now)
    pos = book["positions"].get(symbol)
    metadata, closing = {}, False
    if side == "SELL" and not existing:
        if not pos or pos["units"] <= 0:
            await _reject(user, now, client_order_id, symbol, side, quantity, quote_price,
                          f"No open paper position in {symbol} to sell (paper trading is long-only)")
        if close_all:
            units = pos["units"]
            quantity = format((units * price).quantize(Decimal("0.00000001")), "f")
        else:
            units = base_units(_positive(quantity, "quantity"), price)
            if units > pos["units"]:
                await _reject(user, now, client_order_id, symbol, side, quantity, quote_price,
                              "Sell exceeds open paper position")
        asset_class = pos["asset_class"]
        metadata, closing = {"source_position_id": f"{user['id']}:{symbol}"}, True
    elif side == "SELL":
        units, metadata, closing = Decimal(existing.get("base_qty") or "0"), {"source_position_id": f"{user['id']}:{symbol}"}, True
        quantity = existing["quantity"]
    else:
        units = base_units(_positive(quantity, "quantity"), price)
    intent = OrderIntent(
        user_id=user["id"], broker="kaos_paper", account_id=f"{user['id']}:{PAPER_ACCOUNT}",
        client_order_id=client_order_id, symbol=symbol, asset_class=AssetClass(asset_class),
        side=side, order_kind=OrderKind.MARKET, quantity=quantity, quantity_unit="QUOTE",
        strategy_signal_id="manual", metadata=metadata)
    snapshot = build_snapshot(book, quote_price, now, await kill_switch_active(),
                              quote_timestamp=market_quote.quote_time if market_quote else None)
    try:
        report = await _pipeline.submit(intent, snapshot, closing_position=closing)
    except (RiskRejected, BrokerUnavailable) as exc:
        await _reject(user, now, client_order_id, symbol, side, quantity, quote_price, str(exc))
    if existing:
        return existing
    doc = {"user_id": user["id"], "client_order_id": client_order_id, "symbol": symbol, "asset_class": asset_class,
           "side": side, "quantity": quantity, "quote_price": quote_price, "fill_price": quote_price,
           "base_qty": format(units, "f"), "fill_type": "SIMULATED_MARKET_QUOTE" if market_quote else "SIMULATED",
           "quote_provenance":market_quote.provenance() if market_quote else None,
           "state": report.state.value, "broker": report.broker, "paper": True, "created_at": now.isoformat()}
    if side == "SELL":
        avg = pos["cost"] / pos["units"]
        doc["realized_pnl"] = money(Decimal(quantity) - avg * units)
    await db.paper_orders.update_one(key, {"$setOnInsert": doc}, upsert=True)
    return await db.paper_orders.find_one(key, {"_id": 0})


@router.post("/orders")
async def place_paper_order(req: PaperOrderReq, user: dict = Depends(get_current_user)):
    return await _submit(user, req.symbol, req.asset_class, req.side, req.quantity, req.quote_price, req.client_order_id)


@router.post("/orders/market")
async def place_market_derived_paper_order(req: MarketPaperOrderReq, user: dict = Depends(get_current_user)):
    """Market-derived *simulation*. Never accepts a client quote or routes live.

    Only a Coinbase public spot market quote is supported today. Server quote
    timestamp goes to the actual pretrade risk age check (<=10s).
    """
    import re
    from datetime import datetime, timezone
    symbol=req.symbol.upper()
    if not re.fullmatch(r"[A-Z0-9]{2,10}-[A-Z]{3,5}",symbol):
        raise HTTPException(422,"Invalid crypto spot symbol")
    try:
        quote=await get_quote(symbol,"CRYPTO_SPOT")
    except QuoteUnavailable as exc:
        raise HTTPException(503,str(exc)) from exc
    now=datetime.now(timezone.utc)
    age=(now-quote.quote_time).total_seconds()
    if age<0 or age>RiskLimits().max_price_age_seconds:
        raise HTTPException(503,"Missing or stale market-derived quote")
    price=quote.ask if req.side=="BUY" else quote.bid
    return await _submit(user,symbol,req.asset_class,req.side,req.quantity,
                         str(price),req.client_order_id,market_quote=quote)


@router.post("/positions/{symbol}/close")
async def close_paper_position(symbol: str, req: ClosePositionReq, user: dict = Depends(get_current_user)):
    return await _submit(user, symbol, "CRYPTO_SPOT", "SELL", "0", req.quote_price, req.client_order_id, close_all=True)


@router.get("/orders")
async def list_paper_orders(user: dict = Depends(get_current_user)):
    orders = await db.paper_orders.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)
    rejected = await db.paper_order_rejections.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)
    book = await _user_book(user, datetime.now(timezone.utc))
    return {"orders": orders, "rejected": rejected, "paper": True, "kill_switch": await kill_switch_active(),
            "book": book_view(book)}


@router.post("/kill-switch")
async def set_kill_switch(req: KillSwitchReq, admin: dict = Depends(admin_dep)):
    await set_setting("paper_kill_switch", req.active)
    await audit_log(admin, "paper.kill_switch", "settings", "paper_kill_switch", {"active": req.active})
    return {"kill_switch": req.active}
