"""Paper-only order API on top of DurablePaperPipeline. Never routes to a live broker.

Two execution kinds, always labelled on the order:
- market_data_paper: the server fetches a timestamped quote (market_data.py) and fills
  BUY at the ask / SELL at the bid; stale quotes are refused by the risk engine.
- manual_demo: the caller types the price. Demo only, not a market fill.
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
from kaos_risk_engine import check_order
import kaos_structure_v2
import market_data
from pymongo.errors import DuplicateKeyError

router = APIRouter(prefix="/api/v1/paper", tags=["paper-trading"])
admin_dep = require_role("admin")

PAPER_ACCOUNT = "paper-default"
PAPER_STARTING_BALANCE = Decimal("100")
# Simulated taker fee applied to every paper fill. An assumption, not a broker-quoted rate.
PAPER_FEE_RATE = Decimal(os.environ.get("KAOS_PAPER_FEE_RATE", "0.006"))
FEE_RATE_MAX = Decimal("0.02")
SLIPPAGE_BPS_MAX = 100
MAX_SPREAD_FRACTION = Decimal("0.01")  # refuse quotes whose bid/ask spread exceeds 1% of mid
FEE_MODEL = "Illustrative research assumption set per session; not a Coinbase or broker fee quote."
QUOTE_DELIVERY = "polling"  # REST request per order and every 5 s in clients; no streaming feed yet
SIGNAL_TTL_SECONDS = 120
PAPER_BROKERS = [
    {"id": "kaos_paper_coinbase", "name": "KAOS Paper (Coinbase market data)", "available": True,
     "asset_classes": ["CRYPTO_SPOT"], "note": "Simulated fills at live Coinbase public quotes. No real orders."},
    {"id": "pocket_option", "name": "Pocket Option", "available": False,
     "note": "No authorized market-data API. Pocket Option trading runs in the KAOS Chrome extension."},
    {"id": "coinbase_live", "name": "Coinbase (live)", "available": False,
     "note": "Real-money trading is locked pending review."},
]

_registry = BrokerRegistry()
_registry.register(PaperAdapter(), enabled=True, paper_only=True)
_pipeline = DurablePaperPipeline(
    _registry, RiskLimits(), PaperOrderJournal(os.environ.get("KAOS_PAPER_JOURNAL_PATH", "/tmp/kaos_paper_journal.db")))


class PaperOrderReq(BaseModel):
    symbol: str = Field(min_length=1, max_length=30)
    asset_class: Literal["CRYPTO_SPOT", "FOREX", "EQUITY"] = "CRYPTO_SPOT"
    side: Literal["BUY", "SELL"] = "BUY"
    quantity: str = Field(description="Quote-currency notional, e.g. '10' = $10")
    quote_price: Optional[str] = Field(default=None, description="Omit for a market-data fill; set for the manual demo")
    client_order_id: Optional[str] = Field(default=None, max_length=64)


class ClosePositionReq(BaseModel):
    quote_price: Optional[str] = None
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


async def _submit(user, symbol, asset_class, side, quantity, quote_price, client_order_id, *, close_all=False,
                  signal_id=None):
    now = datetime.now(timezone.utc)
    symbol = symbol.upper()
    client_order_id = client_order_id or f"web-{uuid.uuid4().hex[:16]}"
    key = {"user_id": user["id"], "client_order_id": client_order_id}
    existing = await db.paper_orders.find_one(key, {"_id": 0})
    book = await _user_book(user, now)
    pos = book["positions"].get(symbol)
    quote, quote_ts = None, None
    fee_rate, slip_bps = await _session_costs(user)
    if quote_price is None:
        if existing:
            if existing.get("execution_kind") != "market_data_paper" or existing["symbol"] != symbol or existing["side"] != side \
                    or (not close_all and Decimal(existing["quantity"]) != _positive(quantity, "quantity")):
                raise HTTPException(status_code=409, detail="client_order_id reused with different order details")
            return existing
        try:
            quote = await market_data.get_quote(symbol, pos["asset_class"] if (side == "SELL" and pos) else asset_class)
        except market_data.QuoteUnavailable as exc:
            raise HTTPException(status_code=503, detail=f"Market data unavailable: {exc}")
        mid = (quote.bid + quote.ask) / 2
        if (quote.ask - quote.bid) / mid > MAX_SPREAD_FRACTION:
            await _reject(user, now, client_order_id, symbol, side, quantity, str(quote.ask),
                          f"Quote spread {quote.bid}/{quote.ask} exceeds {MAX_SPREAD_FRACTION:%} of mid; refusing unrealistic quote")
        adj = Decimal(slip_bps) / Decimal(10000)
        px = quote.ask * (1 + adj) if side == "BUY" else quote.bid * (1 - adj)
        quote_price, quote_ts = format(px.quantize(Decimal("0.00000001")).normalize(), "f"), quote.quote_time
    price = _positive(quote_price, "quote price")
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
        strategy_signal_id=signal_id or "manual", metadata=metadata)
    snapshot = build_snapshot(book, quote_price, now, await kill_switch_active(), quote_ts)
    try:
        report = await _pipeline.submit(intent, snapshot, closing_position=closing)
    except (RiskRejected, BrokerUnavailable) as exc:
        await _reject(user, now, client_order_id, symbol, side, quantity, quote_price, str(exc))
    if existing:
        return existing
    doc = {"user_id": user["id"], "client_order_id": client_order_id, "symbol": symbol, "asset_class": asset_class,
           "side": side, "quantity": quantity, "quote_price": quote_price, "fill_price": quote_price,
           "base_qty": format(units, "f"), "fill_type": "SIMULATED",
           "execution_kind": "market_data_paper" if quote else "manual_demo",
           "signal_id": signal_id, "fee_rate": str(fee_rate), "fee_model": FEE_MODEL,
           "slippage_bps": slip_bps if quote else 0,
           "fee": format((Decimal(quantity) * fee_rate).quantize(Decimal("0.00000001")), "f"),
           "quote": quote.provenance() if quote else None,
           "state": report.state.value, "broker": report.broker, "paper": True, "created_at": now.isoformat()}
    if side == "SELL":
        avg = pos["cost"] / pos["units"]
        doc["realized_pnl"] = money(Decimal(quantity) - Decimal(doc["fee"]) - avg * units)
    try:
        await db.paper_orders.update_one(key, {"$setOnInsert": doc}, upsert=True)
    except DuplicateKeyError:
        pass  # a concurrent request with the same client_order_id won; return its order
    return await db.paper_orders.find_one(key, {"_id": 0})


@router.get("/quote/{symbol}")
async def paper_quote(symbol: str, asset_class: str = "CRYPTO_SPOT", user: dict = Depends(get_current_user)):
    try:
        q = await market_data.get_quote(symbol, asset_class)
        age = (datetime.now(timezone.utc) - q.quote_time).total_seconds()
        return {**q.provenance(), "delivery": QUOTE_DELIVERY, "age_seconds": round(age, 1),
                "max_age_seconds": _pipeline.limits.max_price_age_seconds}
    except market_data.QuoteUnavailable as exc:
        raise HTTPException(status_code=503, detail=f"Market data unavailable: {exc}")


@router.post("/orders")
async def place_paper_order(req: PaperOrderReq, user: dict = Depends(get_current_user)):
    return await _submit(user, req.symbol, req.asset_class, req.side, req.quantity, req.quote_price, req.client_order_id)


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


# ----- connected paper trading session: broker -> candles -> strategy signal -> risk -> paper fill -----

class SessionReq(BaseModel):
    broker: str = "kaos_paper_coinbase"
    symbol: str = Field(default="BTC-USD", min_length=1, max_length=30)
    granularity: int = 60
    notional: str = "10"
    fee_rate: str = str(PAPER_FEE_RATE)
    slippage_bps: int = 0


async def _session_costs(user):
    doc = await db.paper_sessions.find_one({"user_id": user["id"]}, {"_id": 0}) or {}
    return Decimal(str(doc.get("fee_rate", PAPER_FEE_RATE))), int(doc.get("slippage_bps", 0))


class ExecuteSignalReq(BaseModel):
    notional: str = "10"


@router.get("/brokers")
async def paper_brokers(user: dict = Depends(get_current_user)):
    return {"brokers": PAPER_BROKERS}


@router.get("/session")
async def get_session(user: dict = Depends(get_current_user)):
    doc = await db.paper_sessions.find_one({"user_id": user["id"]}, {"_id": 0})
    return doc or {"user_id": user["id"], **SessionReq().model_dump()}


@router.put("/session")
async def put_session(req: SessionReq, user: dict = Depends(get_current_user)):
    broker = next((b for b in PAPER_BROKERS if b["id"] == req.broker), None)
    if not broker or not broker["available"]:
        raise HTTPException(status_code=422, detail=(broker or {}).get("note", "Unknown broker"))
    if req.granularity not in market_data.GRANULARITIES:
        raise HTTPException(status_code=422, detail="Unsupported candle size")
    _positive(req.notional, "notional")
    try:
        fee = Decimal(req.fee_rate)
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid fee rate")
    if not fee.is_finite() or fee < 0 or fee > FEE_RATE_MAX:
        raise HTTPException(status_code=422, detail=f"Fee rate must be between 0 and {FEE_RATE_MAX} (2%) per side")
    if not 0 <= req.slippage_bps <= SLIPPAGE_BPS_MAX:
        raise HTTPException(status_code=422, detail=f"Slippage must be between 0 and {SLIPPAGE_BPS_MAX} bps")
    doc = {**req.model_dump(), "fee_rate": str(fee), "fee_model": FEE_MODEL, "symbol": req.symbol.upper(), "user_id": user["id"],
           "updated_at": datetime.now(timezone.utc).isoformat()}
    await db.paper_sessions.update_one({"user_id": user["id"]}, {"$set": doc}, upsert=True)
    return doc


@router.get("/candles/{symbol}")
async def paper_candles(symbol: str, granularity: int = 60, user: dict = Depends(get_current_user)):
    try:
        return await market_data.get_candles(symbol, "CRYPTO_SPOT", granularity)
    except market_data.QuoteUnavailable as exc:
        raise HTTPException(status_code=503, detail=f"Market data unavailable: {exc}")


async def _risk_preview(user, symbol, action, notional, quote):
    """Run the same risk engine the order path uses, without submitting anything."""
    now = datetime.now(timezone.utc)
    book = await _user_book(user, now)
    pos = book["positions"].get(symbol)
    if action == "HOLD":
        return {"approved": False, "reason": "No trade: the strategy did not signal."}
    if action == "SELL" and not (pos and pos["units"] > 0):
        return {"approved": False, "reason": "SELL signal but no open paper position (paper trading is long-only)."}
    price = quote.ask if action == "BUY" else quote.bid
    closing = action == "SELL"
    qty = format((pos["units"] * price).quantize(Decimal("0.00000001")), "f") if closing else notional
    intent = OrderIntent(
        user_id=user["id"], broker="kaos_paper", account_id=f"{user['id']}:{PAPER_ACCOUNT}",
        client_order_id="preview", symbol=symbol, asset_class=AssetClass.CRYPTO_SPOT, side=action,
        order_kind=OrderKind.MARKET, quantity=qty, quantity_unit="QUOTE", strategy_signal_id="preview",
        metadata={"source_position_id": f"{user['id']}:{symbol}"} if closing else {})
    snap = build_snapshot(book, str(price), now, await kill_switch_active(), quote.quote_time)
    try:
        check_order(intent, PaperAdapter().capabilities, _pipeline.limits, snap, closing_position=closing)
    except RiskRejected as exc:
        return {"approved": False, "reason": str(exc)}
    return {"approved": True, "reason": ("Exit of open position" if closing else f"BUY ${notional}") +
            f" at {price} passes notional, exposure, daily-loss, position-count, quote-age and kill-switch checks."}


@router.post("/signals/{symbol}")
async def generate_signal(symbol: str, req: ExecuteSignalReq, granularity: int = 60,
                          user: dict = Depends(get_current_user)):
    """Run the KAOS strategy on the latest closed candles and record the signal with its reasons and risk decision."""
    symbol = symbol.upper()
    _positive(req.notional, "notional")
    try:
        candles = await market_data.get_candles(symbol, "CRYPTO_SPOT", granularity)
        quote = await market_data.get_quote(symbol, "CRYPTO_SPOT")
    except market_data.QuoteUnavailable as exc:
        raise HTTPException(status_code=503, detail=f"Market data unavailable: {exc}")
    result = kaos_structure_v2.evaluate(candles["candles"])
    risk = await _risk_preview(user, symbol, result["action"], req.notional, quote)
    doc = {"signal_id": f"sig-{uuid.uuid4().hex[:16]}", "user_id": user["id"], "symbol": symbol,
           "strategy": kaos_structure_v2.STRATEGY_NAME, "strategy_status": kaos_structure_v2.STRATEGY_STATUS,
           "granularity": granularity, **result, "quote": quote.provenance(), "notional": req.notional,
           "risk": risk, "status": "PENDING" if risk["approved"] else "NOT_TRADED",
           "created_at": datetime.now(timezone.utc).isoformat()}
    await db.paper_signals.insert_one(dict(doc))
    return doc


@router.post("/signals/{signal_id}/execute")
async def execute_signal(signal_id: str, user: dict = Depends(get_current_user)):
    sig = await db.paper_signals.find_one({"signal_id": signal_id, "user_id": user["id"]}, {"_id": 0})
    if not sig:
        raise HTTPException(status_code=404, detail="Signal not found")
    cid = f"exec-{signal_id}"
    if sig.get("status") == "EXECUTED":
        return await db.paper_orders.find_one({"user_id": user["id"], "client_order_id": cid}, {"_id": 0})
    if sig["action"] == "HOLD" or not sig["risk"]["approved"]:
        raise HTTPException(status_code=409, detail=f"Signal not tradable: {sig['risk']['reason']}")
    age = (datetime.now(timezone.utc) - datetime.fromisoformat(sig["created_at"])).total_seconds()
    if age > SIGNAL_TTL_SECONDS:
        await db.paper_signals.update_one({"signal_id": signal_id, "status": "PENDING"}, {"$set": {"status": "EXPIRED"}})
        raise HTTPException(status_code=409, detail="Signal expired; generate a new one")
    # Atomic claim: concurrent clicks / clients cannot both reach the order path for one signal.
    claim = await db.paper_signals.update_one({"signal_id": signal_id, "user_id": user["id"], "status": "PENDING"},
                                              {"$set": {"status": "EXECUTING"}})
    if not claim.modified_count:
        cur = await db.paper_signals.find_one({"signal_id": signal_id}, {"_id": 0})
        if cur and cur.get("status") == "EXECUTED":
            return await db.paper_orders.find_one({"user_id": user["id"], "client_order_id": cid}, {"_id": 0})
        raise HTTPException(status_code=409, detail=f"Signal is {(cur or {}).get('status', 'unavailable')}")
    try:
        if sig["action"] == "BUY":
            order = await _submit(user, sig["symbol"], "CRYPTO_SPOT", "BUY", sig["notional"], None, cid, signal_id=signal_id)
        else:
            order = await _submit(user, sig["symbol"], "CRYPTO_SPOT", "SELL", "0", None, cid, close_all=True, signal_id=signal_id)
    except HTTPException as exc:
        await db.paper_signals.update_one({"signal_id": signal_id}, {"$set": {
            "status": "REJECTED", "reject_reason": str(exc.detail),
            "risk_at_execution": {"approved": False, "reason": str(exc.detail), "http_status": exc.status_code}}})
        raise
    await db.paper_signals.update_one({"signal_id": signal_id}, {"$set": {
        "status": "EXECUTED", "client_order_id": cid,
        "risk_at_execution": {"approved": True, "reason": "Re-checked by the risk engine against the fresh execution quote.",
                              "quote": order.get("quote")}}})
    return order


@router.get("/signals")
async def list_signals(user: dict = Depends(get_current_user)):
    return {"signals": await db.paper_signals.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(50)}
