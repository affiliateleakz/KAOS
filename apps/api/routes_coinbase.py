"""Coinbase Advanced spot order gateway for KAOS FastAPI/Motor.

Live orders are disabled by default and require explicit unexpired consent.
No AI or placeholder signals are accepted. This is a controlled manual gateway,
NOT a fully autonomous strategy worker.
"""
import asyncio
import os
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Literal, Optional
from cryptography.fernet import Fernet
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from pymongo.errors import DuplicateKeyError
from auth import get_current_user
from db import db, now_iso
from services_trading import get_entitlements
from services import get_setting

router = APIRouter(prefix="/api/v1/coinbase-live", tags=["coinbase-live"])
PRODUCT = re.compile(r"^[A-Z0-9]{2,20}-USD$")
CID = re.compile(r"^[A-Za-z0-9_-]{16,64}$")

class OrderRequest(BaseModel):
    client_order_id: str
    product_id: str
    side: Literal["BUY", "SELL"]
    quote_size: Optional[str] = None
    base_size: Optional[str] = None
    source_buy_client_order_id: Optional[str] = None

class ReconcileRequest(BaseModel):
    client_order_id: str

class PreviewRequest(BaseModel):
    product_id: str
    side: Literal["BUY", "SELL"]
    quote_size: Optional[str] = None
    base_size: Optional[str] = None


def positive(value, maximum=None):
    try:
        x = Decimal(str(value))
        if not x.is_finite() or x <= 0 or (maximum is not None and x > Decimal(str(maximum))):
            raise ValueError()
        return format(x, "f")
    except (ValueError, InvalidOperation, TypeError):
        raise HTTPException(422, "Invalid size or risk limit")

async def authorized(request, user):
    if not request.headers.get("authorization", "").startswith("Bearer "):
        raise HTTPException(403, "Bearer authorization required")
    if user.get("account_status", "active") != "active" or user.get("extension_access_revoked"):
        raise HTTPException(403, "Account disabled")
    if user.get("membership_status") not in ("ACTIVE", "TRIAL"):
        raise HTTPException(403, "Active KAOS membership required")
    ent = await get_entitlements(user)
    if not ent.get("botAccess"):
        raise HTTPException(403, "Bot membership access required")
    if os.getenv("KAOS_COINBASE_LIVE_ORDERS", "disabled") != "enabled":
        raise HTTPException(403, "Coinbase live orders disabled")
    consent = await db.coinbase_live_consent.find_one({"user_id": user["id"], "enabled": True})
    expiry = consent.get("expires_at") if consent else None
    if isinstance(expiry, str):
        try: expiry = datetime.fromisoformat(expiry.replace("Z", "+00:00"))
        except ValueError: expiry = None
    if expiry and expiry.tzinfo is None: expiry = expiry.replace(tzinfo=timezone.utc)
    if not expiry or expiry <= datetime.now(timezone.utc):
        raise HTTPException(403, "Unexpired explicit live-trading consent required")
    if await db.coinbase_emergency_stops.find_one({"user_id": user["id"], "stopped": True}):
        raise HTTPException(403, "Emergency stop active")
    if await get_setting("paper_kill_switch", False):  # platform-wide emergency stop (admin) also halts live orders
        raise HTTPException(403, "Platform emergency stop active")
    return consent

async def connection(user_id):
    row = await db.broker_connections.find_one({"user_id": user_id, "broker": "coinbase", "verified": True})
    if not row: raise HTTPException(403, "Verified Coinbase connection required")
    if not os.getenv("KAOS_BROKER_VAULT_KEY"):
        raise HTTPException(503, "Broker vault not configured")
    return row

def make_client(row):
    from coinbase.rest import RESTClient
    vault = Fernet(os.environ["KAOS_BROKER_VAULT_KEY"].encode())
    key = vault.decrypt(row["key_name_enc"].encode()).decode()
    secret = vault.decrypt(row["private_key_enc"].encode()).decode()
    return RESTClient(api_key=key, api_secret=secret, timeout=12)

def asdict(value):
    if hasattr(value, "to_dict"): return value.to_dict()
    if isinstance(value, dict): return value
    raise ValueError("Unexpected Coinbase response")

@router.get("/status")
async def status(request: Request, user: dict = Depends(get_current_user)):
    # No consent or credentials disclosed to the browser.
    return {"enabled": os.getenv("KAOS_COINBASE_LIVE_ORDERS", "disabled") == "enabled",
            "automated_worker": False, "recovery_worker_available": True, "authenticated": True}

@router.post("/orders")
async def order(req: OrderRequest, request: Request, user: dict = Depends(get_current_user)):
    consent = await authorized(request, user)
    if not PRODUCT.fullmatch(req.product_id) or not CID.fullmatch(req.client_order_id):
        raise HTTPException(422, "Invalid product or client order id")
    uid = user["id"]
    key = {"user_id": uid, "broker": "coinbase", "client_order_id": req.client_order_id}
    # Stable order ID is reserved before any exchange call.
    if await db.coinbase_order_intents.find_one(key):
        raise HTTPException(409, "Order ID already reserved; reconcile, never resubmit")
    source = None
    slot = None
    if req.side == "BUY":
        limit = min(Decimal(os.getenv("KAOS_COINBASE_MAX_ORDER_USD", "25")),
                    Decimal(str(consent.get("max_order_usd", "25"))))
        size = positive(req.quote_size, limit)
        if req.base_size is not None: raise HTTPException(422, "BUY requires quote_size only")
        # Atomic slot is the authority for one active BUY per account/product.
        # Unique Mongo _id ensures concurrent requests cannot both reserve it.
        slot = {"_id": f"{uid}:coinbase:{req.product_id}", "user_id": uid,
                "product_id": req.product_id, "client_order_id": req.client_order_id,
                "created_at": now_iso()}
    else:
        if req.quote_size is not None: raise HTTPException(422, "SELL requires base_size only")
        source = await db.coinbase_order_intents.find_one({"user_id": uid, "broker": "coinbase",
            "client_order_id": req.source_buy_client_order_id, "product_id": req.product_id,
            "side": "BUY", "state": "FILLED"})
        if not source or not source.get("filled_size"):
            raise HTTPException(409, "Verified KAOS BUY position required")
        size = positive(req.base_size, source["filled_size"])
        if Decimal(size) != Decimal(str(source["filled_size"])):
            raise HTTPException(422, "Full position exit required")
    conn = await connection(uid)
    # Atomic exit reservation blocks duplicate exits.
    if source:
        locked = await db.coinbase_order_intents.update_one({"_id": source["_id"], "state": "FILLED",
            "exit_client_order_id": {"$exists": False}}, {"$set": {"state": "EXIT_SUBMITTING",
            "exit_client_order_id": req.client_order_id}})
        if locked.modified_count != 1: raise HTTPException(409, "Exit already reserved")
    if slot:
        try:
            await db.coinbase_active_slots.insert_one(slot)
        except DuplicateKeyError:
            raise HTTPException(409, "Existing active or uncertain KAOS position")
        except Exception:
            raise HTTPException(503, "Unable to reserve position slot")
    doc = {**key, "product_id": req.product_id, "side": req.side,
        "quote_size": size if req.side == "BUY" else None,
        "base_size": size if req.side == "SELL" else None,
        "source_buy_client_order_id": req.source_buy_client_order_id if source else None,
        "state": "SUBMITTING", "created_at": now_iso()}
    try:
        await db.coinbase_order_intents.insert_one(doc)
    except DuplicateKeyError:
        if slot:
            await db.coinbase_active_slots.delete_one({"_id": slot["_id"], "client_order_id": req.client_order_id})
        raise HTTPException(409, "Order ID already reserved")
    except Exception:
        if slot:
            await db.coinbase_active_slots.delete_one({"_id": slot["_id"], "client_order_id": req.client_order_id})
        raise HTTPException(503, "Unable to persist order; no exchange call made")
    try:
        def submit():
            client = make_client(conn)
            if req.side == "BUY":
                return asdict(client.market_order_buy(client_order_id=req.client_order_id,
                    product_id=req.product_id, quote_size=size))
            return asdict(client.market_order_sell(client_order_id=req.client_order_id,
                product_id=req.product_id, base_size=size))
        response = await asyncio.to_thread(submit)
        order_id = (response.get("success_response") or {}).get("order_id")
        state = "ACCEPTED" if response.get("success") and order_id else "REJECTED"
        await db.coinbase_order_intents.update_one(key, {"$set": {"state": state,
            "order_id": order_id, "updated_at": now_iso()}})
        if state == "REJECTED" and slot:
            # Only a definitive exchange rejection can release a BUY slot.
            await db.coinbase_active_slots.delete_one({"_id": slot["_id"],
                "client_order_id": req.client_order_id})
        if state == "REJECTED" and source:
            await db.coinbase_order_intents.update_one({"_id": source["_id"],
                "exit_client_order_id": req.client_order_id},
                {"$set": {"state": "FILLED"}, "$unset": {"exit_client_order_id": ""}})
        return {"client_order_id": req.client_order_id, "order_id": order_id, "state": state,
                "note": "Accepted does not mean filled; reconcile before position changes"}
    except Exception:
        await db.coinbase_order_intents.update_one(key, {"$set": {
            "state": "UNKNOWN_RECONCILIATION_REQUIRED", "updated_at": now_iso()}})
        raise HTTPException(502, "Unknown exchange outcome; do not retry this order")

@router.post("/reconcile")
async def reconcile(req: ReconcileRequest, request: Request, user: dict = Depends(get_current_user)):
    await authorized(request, user)
    return await reconcile_order(user["id"], req.client_order_id)

async def reconcile_order(uid: str, client_order_id: str):
    """Server-owned fill reconciliation; callable by the recovery worker.

    Never infer a fill from order acceptance alone. A missing order ID
    stays uncertain until independently resolved by Coinbase.
    """
    key = {"user_id": uid, "broker": "coinbase", "client_order_id": client_order_id}
    intent = await db.coinbase_order_intents.find_one(key)
    if not intent or not intent.get("order_id"):
        raise HTTPException(409, "No exchange order ID; manual reconciliation required")
    conn = await connection(uid)
    def fetch():
        client = make_client(conn)
        order_data = asdict(client.get_order(intent["order_id"]))
        exchange_order = order_data.get("order") or order_data
        if str(exchange_order.get("order_id")) != str(intent["order_id"]):
            raise ValueError("Order identity mismatch")
        fills = []
        cursor = None
        seen = set()
        while True:
            args = {"order_ids": [intent["order_id"]], "limit": 100}
            if cursor: args["cursor"] = cursor
            page = asdict(client.get_fills(**args))
            batch = page.get("fills")
            if not isinstance(batch, list): raise ValueError("Invalid fills page")
            fills.extend(asdict(x) for x in batch)
            more = page.get("has_next")
            if more is None and len(batch) == 100:
                raise ValueError("Ambiguous pagination; manual review required")
            if not more: break
            cursor = page.get("cursor")
            if not cursor or cursor in seen or len(seen) >= 1000:
                raise ValueError("Incomplete fills pagination")
            seen.add(cursor)
        return exchange_order, fills
    try:
        exchange_order, raw_fills = await asyncio.to_thread(fetch)
        seen = {}
        for fill in raw_fills:
            if str(fill.get("order_id")) != str(intent["order_id"]):
                raise ValueError("Fill order mismatch")
            trade_id = str(fill.get("trade_id") or "")
            if not trade_id: raise ValueError("Missing fill trade ID")
            sz = positive(fill.get("size"))
            price = positive(fill.get("price"))
            fee = Decimal(str(fill.get("commission", "0")))
            if not fee.is_finite() or fee < 0: raise ValueError("Invalid fee")
            item = {"user_id": uid, "broker": "coinbase", "trade_id": trade_id,
                "order_id": str(intent["order_id"]), "size": sz, "price": price,
                "commission": str(fee), "product_id": intent["product_id"], "side": intent["side"]}
            if trade_id in seen and seen[trade_id] != item: raise ValueError("Conflicting fill")
            seen[trade_id] = item
        for item in seen.values():
            existing = await db.coinbase_trade_fills.find_one({"user_id": uid,
                "broker": "coinbase", "trade_id": item["trade_id"]})
            if existing:
                if any(str(existing.get(k)) != str(v) for k, v in item.items()):
                    raise ValueError("Conflicting persisted fill")
            else:
                try: await db.coinbase_trade_fills.insert_one(item)
                except DuplicateKeyError: pass
        cursor = db.coinbase_trade_fills.find({"user_id": uid,
            "broker": "coinbase", "order_id": str(intent["order_id"])})
        all_fills = await cursor.to_list(length=10001)
        if len(all_fills) > 10000:
            raise ValueError("Fill ledger exceeds reconciliation safety limit")
        size = sum((Decimal(x["size"]) for x in all_fills), Decimal(0))
        notional = sum((Decimal(x["size"]) * Decimal(x["price"]) for x in all_fills), Decimal(0))
        fees = sum((Decimal(x["commission"]) for x in all_fills), Decimal(0))
        reported = exchange_order.get("filled_size")
        if reported is not None:
            try:
                reported_size = Decimal(str(reported))
            except (InvalidOperation, ValueError):
                raise ValueError("Invalid exchange filled_size")
            if not reported_size.is_finite() or reported_size < 0 or reported_size != size:
                raise ValueError("Exchange and persisted fill sizes disagree")
        status = str(exchange_order.get("status", "")).upper()
        if status == "FILLED": state = "FILLED" if size > 0 else "FILL_MISMATCH_REVIEW"
        elif status in ("CANCELLED", "EXPIRED", "FAILED"):
            state = "PARTIAL_FILL_REVIEW" if size > 0 else "CLOSED_UNFILLED"
        else: state = "PARTIAL_FILL_REVIEW" if size > 0 else "OPEN"
        await db.coinbase_order_intents.update_one(key, {"$set": {"state": state,
            "filled_size": str(size), "fill_notional": str(notional), "fill_fees": str(fees),
            "exchange_status": status, "updated_at": now_iso()}})
        if intent["side"] == "BUY" and state == "CLOSED_UNFILLED":
            await db.coinbase_active_slots.delete_one({"_id": f'{uid}:coinbase:{intent["product_id"]}',
                "client_order_id": intent["client_order_id"]})
        if intent["side"] == "SELL" and state == "FILLED":
            source = await db.coinbase_order_intents.find_one({"user_id": uid,
                "broker": "coinbase", "client_order_id": intent["source_buy_client_order_id"]})
            if not source or Decimal(str(source.get("filled_size", "0"))) != size:
                await db.coinbase_order_intents.update_one(key, {"$set": {
                    "state": "EXIT_QUANTITY_REVIEW", "updated_at": now_iso()}})
                raise HTTPException(409, "Exit quantity does not match source BUY; manual review")
            await db.coinbase_order_intents.update_one({"user_id": uid,
                "broker": "coinbase", "client_order_id": intent["source_buy_client_order_id"],
                "exit_client_order_id": intent["client_order_id"]},
                {"$set": {"state": "CLOSED", "updated_at": now_iso()}})
            await db.coinbase_active_slots.delete_one({"_id": f'{uid}:coinbase:{intent["product_id"]}',
                "client_order_id": intent["source_buy_client_order_id"]})
        return {"client_order_id": client_order_id, "state": state,
                "filled_size": str(size), "notional": str(notional), "fees": str(fees)}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(502, "Could not safely reconcile Coinbase order; manual review required")


INTENT_FIELDS = ("client_order_id", "order_id", "product_id", "side", "quote_size", "base_size", "state",
                 "exchange_status", "filled_size", "fill_notional", "fill_fees", "created_at", "updated_at")


@router.post("/preview")
async def preview(req: PreviewRequest, user: dict = Depends(get_current_user)):
    """Ask Coinbase to preview (not place) a market order: expected fill, fees, slippage and errors.

    Works while live submission is disabled; needs a verified connection whose key has Trade permission.
    """
    if not PRODUCT.fullmatch(req.product_id):
        raise HTTPException(422, "Invalid product")
    if req.side == "BUY" and (not req.quote_size or req.base_size):
        raise HTTPException(422, "BUY preview requires quote_size only")
    if req.side == "SELL" and (not req.base_size or req.quote_size):
        raise HTTPException(422, "SELL preview requires base_size only")
    size = positive(req.quote_size or req.base_size)
    conn = await connection(user["id"])
    def call():
        client = make_client(conn)
        if req.side == "BUY":
            return asdict(client.preview_market_order_buy(product_id=req.product_id, quote_size=size))
        return asdict(client.preview_market_order_sell(product_id=req.product_id, base_size=size))
    try:
        data = await asyncio.to_thread(call)
    except Exception as exc:
        raise HTTPException(502, f"Coinbase preview failed ({type(exc).__name__})")
    keep = ("order_total", "commission_total", "quote_size", "base_size", "best_bid", "best_ask", "slippage",
            "average_filled_price", "errs", "warning", "est_average_filled_price")
    return {"preview": {k: data.get(k) for k in keep if k in data}, "placed": False,
            "live_orders_enabled": os.getenv("KAOS_COINBASE_LIVE_ORDERS", "disabled") == "enabled"}


@router.get("/orders")
async def list_intents(user: dict = Depends(get_current_user)):
    """KAOS-originated Coinbase orders with their reconciliation state (same list on every device)."""
    rows = await db.coinbase_order_intents.find({"user_id": user["id"], "broker": "coinbase"}).sort(
        "created_at", -1).to_list(200)
    return {"orders": [{k: r.get(k) for k in INTENT_FIELDS} for r in rows]}


@router.post("/cancel")
async def cancel(req: ReconcileRequest, request: Request, user: dict = Depends(get_current_user)):
    """Cancel an open KAOS order on Coinbase, then reconcile it. Same gates as submission."""
    await authorized(request, user)
    key = {"user_id": user["id"], "broker": "coinbase", "client_order_id": req.client_order_id}
    intent = await db.coinbase_order_intents.find_one(key)
    if not intent or not intent.get("order_id"):
        raise HTTPException(404, "No exchange order for this client order id")
    if intent.get("state") not in ("ACCEPTED", "OPEN", "PARTIAL_FILL_REVIEW"):
        raise HTTPException(409, f"Order is {intent.get('state')}; nothing to cancel")
    conn = await connection(user["id"])
    def call():
        return asdict(make_client(conn).cancel_orders(order_ids=[intent["order_id"]]))
    try:
        data = await asyncio.to_thread(call)
    except Exception as exc:
        raise HTTPException(502, f"Coinbase cancel failed ({type(exc).__name__}); reconcile before retrying")
    result = (data.get("results") or [{}])[0]
    await db.coinbase_order_intents.update_one(key, {"$set": {"cancel_requested_at": now_iso(),
        "cancel_result": {"success": bool(result.get("success")), "failure_reason": result.get("failure_reason")}}})
    try:
        state = await reconcile_order(user["id"], req.client_order_id)
    except HTTPException:
        state = None
    return {"client_order_id": req.client_order_id, "cancel_success": bool(result.get("success")),
            "failure_reason": result.get("failure_reason"), "reconciled": state}
