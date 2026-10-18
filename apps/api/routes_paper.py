"""Paper-only order API on top of DurablePaperPipeline. Never routes to a live broker.

The quote price is caller-supplied until an authorized market-data feed exists,
so results are simulation records only.
"""
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal
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

router = APIRouter(prefix="/api/v1/paper", tags=["paper-trading"])
admin_dep = require_role("admin")

PAPER_ACCOUNT = "paper-default"
PAPER_STARTING_BALANCE = Decimal("100")
OPEN_STATES = {"SUBMITTED", "PARTIALLY_FILLED", "FILLED"}

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


class KillSwitchReq(BaseModel):
    active: bool


def build_snapshot(orders, quote_price, now, emergency_stopped):
    """Risk snapshot from the user's own paper order history."""
    open_orders = [o for o in orders if o.get("state") in OPEN_STATES and o.get("side") == "BUY"]
    exposure = sum((Decimal(o["quantity"]) for o in open_orders), Decimal("0"))
    return RiskSnapshot(
        now=now, quote_timestamp=now, quote_price=quote_price, daily_realized_pnl="0",
        open_exposure=str(exposure), open_positions=len(open_orders),
        available_quote_balance=str(max(PAPER_STARTING_BALANCE - exposure, Decimal("0"))),
        emergency_stopped=emergency_stopped)


async def kill_switch_active():
    return bool(await get_setting("paper_kill_switch", False))


@router.post("/orders")
async def place_paper_order(req: PaperOrderReq, user: dict = Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    client_order_id = req.client_order_id or f"web-{uuid.uuid4().hex[:16]}"
    intent = OrderIntent(
        user_id=user["id"], broker="kaos_paper", account_id=f"{user['id']}:{PAPER_ACCOUNT}",
        client_order_id=client_order_id, symbol=req.symbol.upper(), asset_class=AssetClass(req.asset_class),
        side=req.side, order_kind=OrderKind.MARKET, quantity=req.quantity, quantity_unit="QUOTE",
        strategy_signal_id="manual")
    history = await db.paper_orders.find({"user_id": user["id"]}, {"_id": 0}).to_list(1000)
    snapshot = build_snapshot(history, req.quote_price, now, await kill_switch_active())
    try:
        report = await _pipeline.submit(intent, snapshot)
    except (RiskRejected, BrokerUnavailable) as exc:
        await db.paper_order_rejections.insert_one({
            "user_id": user["id"], "client_order_id": client_order_id, "symbol": intent.symbol,
            "side": req.side, "quantity": req.quantity, "quote_price": req.quote_price,
            "state": "REJECTED", "reason": str(exc), "paper": True, "created_at": now.isoformat()})
        raise HTTPException(status_code=422, detail=f"Paper order rejected: {exc}")
    doc = {"user_id": user["id"], "client_order_id": client_order_id, "symbol": intent.symbol,
           "side": req.side, "quantity": req.quantity, "quote_price": req.quote_price,
           "state": report.state.value, "broker": report.broker, "paper": True, "created_at": now.isoformat()}
    key = {"user_id": user["id"], "client_order_id": client_order_id}
    await db.paper_orders.update_one(key, {"$setOnInsert": doc}, upsert=True)
    return await db.paper_orders.find_one(key, {"_id": 0})


@router.get("/orders")
async def list_paper_orders(user: dict = Depends(get_current_user)):
    orders = await db.paper_orders.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)
    rejected = await db.paper_order_rejections.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return {"orders": orders, "rejected": rejected, "paper": True, "kill_switch": await kill_switch_active()}


@router.post("/kill-switch")
async def set_kill_switch(req: KillSwitchReq, admin: dict = Depends(admin_dep)):
    await set_setting("paper_kill_switch", req.active)
    await audit_log(admin, "paper.kill_switch", "settings", "paper_kill_switch", {"active": req.active})
    return {"kill_switch": req.active}
