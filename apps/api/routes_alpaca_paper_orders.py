"""Owner-only, feature-flagged Alpaca paper BUY preview and submission.

No AI order authority and no live trading. Submit uses a fresh server-side IEX
quote, Alpaca market clock, existing KAOS risk check, and durable order ID.
Any ambiguous broker outcome remains UNKNOWN until explicit reconciliation.
"""
import os
import re
import secrets
from datetime import datetime,timezone,timedelta
from decimal import Decimal,InvalidOperation
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from pymongo.errors import DuplicateKeyError
from pymongo import ReturnDocument

from auth import get_current_user
from db import db,now_iso
from services import get_setting
from services_trading import get_entitlements
from kaos_broker_core import OrderIntent,AssetClass,OrderKind
from kaos_paper_adapter import PaperAdapter
from kaos_risk_engine import check_order,RiskLimits,RiskSnapshot,RiskRejected
from routes_alpaca_paper import credentials
from alpaca_paper_client import (
    paper_request, AlpacaPaperUnavailable,submit_stock_paper_buy,lookup_paper_order
)
from alpaca_paper_quotes import latest_stock_quote,MarketUnavailable

router=APIRouter(prefix="/api/v1/alpaca-paper",tags=["alpaca-paper-orders"])
LIMITS=RiskLimits()
SYMBOL=re.compile(r"[A-Z]{1,5}(?:[.][A-Z])?")

class PreviewReq(BaseModel):
    symbol:str=Field(min_length=1,max_length=6)
    notional:str=Field(min_length=1,max_length=20)

class ConfirmReq(BaseModel):
    preview_id:str=Field(min_length=16,max_length=64)

class ReconcileReq(BaseModel):
    client_order_id:str=Field(pattern=r"^kaos-paper-[a-f0-9]{32}$")


def _notional(value):
    try: result=Decimal(value)
    except (InvalidOperation,ValueError,TypeError) as exc:
        raise HTTPException(422,"Invalid order notional") from exc
    if not result.is_finite() or result<Decimal("1") or result>Decimal(LIMITS.max_order_notional):
        raise HTTPException(422,"Paper stock order must be $1 to $25")
    return result


async def guard(user, *, reconciliation=False):
    if not reconciliation and os.getenv("KAOS_ALPACA_PAPER_ORDERS_ENABLED")!="1":
        raise HTTPException(503,"Alpaca paper orders are not enabled on KAOS")
    owner=os.getenv("KAOS_CANDLE_OWNER_USER_ID","")
    if not owner or user.get("id")!=owner or user.get("role") not in ("admin","super_admin"):
        raise HTTPException(403,"Paper order beta restricted to KAOS owner")
    if user.get("account_status","active")!="active" or user.get("extension_access_revoked"):
        raise HTTPException(403,"Account disabled")
    if not (await get_entitlements(user)).get("botAccess"):
        raise HTTPException(403,"Bot access required")
    if not reconciliation and await get_setting("paper_kill_switch",False):
        raise HTTPException(403,"Paper emergency stop active")
    return await credentials(user)


async def preflight(key,secret,user,symbol,notional):
    account=await paper_request(key,secret,"GET","/v2/account")
    clock=await paper_request(key,secret,"GET","/v2/clock")
    if not account.get("status") in ("ACTIVE","PAPER_ONLY") or account.get("trading_blocked") or not clock.get("is_open"):
        raise HTTPException(409,"Alpaca account blocked or US stock market closed")
    if await get_setting("paper_kill_switch",False):
        raise HTTPException(403,"Paper emergency stop active")
    quote=await latest_stock_quote(key,secret,symbol)
    pos=await paper_request(key,secret,"GET","/v2/positions")
    # Recheck quote age after any slow broker position response.
    now=datetime.now(timezone.utc)
    if not isinstance(pos,list):
        raise HTTPException(503,"Alpaca paper positions unavailable")
    # Conservative account-equity loss proxy; true realized daily P&L
    # needs the broker activity ledger before moving beyond owner beta.
    equity=Decimal(str(account.get("equity","0")))
    last=Decimal(str(account.get("last_equity","0")))
    cash=Decimal(str(account.get("cash","0")))
    if not all(v.is_finite() and v>=0 for v in (equity,last,cash)) or not last:
        raise HTTPException(503,"Cannot verify Alpaca paper account risk balances")
    exposure=sum(
        (abs(Decimal(str(x.get("market_value","0")))) for x in pos),
        Decimal("0"))
    if len(pos)>=LIMITS.max_open_positions:
        raise HTTPException(409,"Paper position count limit reached")
    intent=OrderIntent(
        user_id=user["id"],broker="kaos_paper",account_id=user["id"]+":alpaca_paper",
        client_order_id="preview-only",symbol=symbol,asset_class=AssetClass.EQUITY,
        side="BUY",order_kind=OrderKind.MARKET,quantity=str(notional),
        quantity_unit="QUOTE",strategy_signal_id="manual_paper_confirmed")
    snapshot=RiskSnapshot(now=now,quote_timestamp=datetime.fromisoformat(quote["timestamp"]),
        quote_price=quote["ask"],daily_realized_pnl=str(min(equity-last,Decimal("0"))),
        open_exposure=str(exposure),open_positions=len(pos),
        available_quote_balance=str(cash),emergency_stopped=False)
    try:
        check_order(intent,PaperAdapter.capabilities,LIMITS,snapshot,live=False)
    except (RiskRejected,InvalidOperation,TypeError) as exc:
        raise HTTPException(422,"KAOS paper risk rejected the order") from exc
    return {"symbol":symbol,"notional":format(notional,"f"),
            "quote":quote,"risk":"approved_for_owner_paper_preview",
            "source":"alpaca_stock_iex","market_open":True,
            "paper_only":True,"order_submitted":False}


@router.post("/orders/preview")
async def paper_preview(req:PreviewReq,user:dict=Depends(get_current_user)):
    if not SYMBOL.fullmatch(req.symbol.upper()):
        raise HTTPException(422,"Only US equity tickers supported in this beta")
    notional=_notional(req.notional)
    key,secret=await guard(user)
    try: result=await preflight(key,secret,user,req.symbol.upper(),notional)
    except (MarketUnavailable,AlpacaPaperUnavailable,InvalidOperation) as exc:
        raise HTTPException(503,"Alpaca paper quote/account risk data unavailable") from exc
    now=datetime.now(timezone.utc)
    preview_id=secrets.token_hex(20)
    await db.alpaca_paper_order_previews.insert_one({
        "_id":preview_id,"user_id":user["id"],
        "symbol":req.symbol.upper(),"notional":format(notional,"f"),
        "status":"PREVIEW","created_at":now,"expires_at":now+timedelta(seconds=25)})
    return {**result,"preview_id":preview_id,
            "expires_at":(now+timedelta(seconds=25)).isoformat(),
            "requires_separate_confirmation":True,"ai_order":False}


@router.post("/orders/confirm")
async def paper_confirm(req:ConfirmReq,user:dict=Depends(get_current_user)):
    key,secret=await guard(user)
    now=datetime.now(timezone.utc)
    # Atomic one-use preview claim; never accept arbitrary ticker/quantity.
    preview=await db.alpaca_paper_order_previews.find_one_and_update(
        {"_id":req.preview_id,"user_id":user["id"],"status":"PREVIEW",
         "expires_at":{"$gt":now}},
        {"$set":{"status":"RESERVED","reserved_at":now}},
        return_document=ReturnDocument.AFTER)
    if not preview:
        raise HTTPException(409,"Paper preview used or expired; start a new preview")
    cid="kaos-paper-"+secrets.token_hex(16)
    try:
        await db.alpaca_paper_inflight.insert_one({
            "_id":user["id"],"client_order_id":cid,"created_at":now})
    except DuplicateKeyError:
        await db.alpaca_paper_order_previews.update_one(
            {"_id":req.preview_id},{"$set":{"status":"REJECTED_CONCURRENT"}})
        raise HTTPException(409,"Another paper order is pending reconciliation")
    order={"_id":cid,"client_order_id":cid,"user_id":user["id"],"preview_id":req.preview_id,
           "symbol":preview["symbol"],"notional":preview["notional"],
           "state":"RESERVED","paper_only":True,"ai_order":False,
           "created_at":now_iso(),"broker":"alpaca_paper"}
    await db.alpaca_paper_manual_orders.insert_one(order)
    try:
        await preflight(key,secret,user,preview["symbol"],_notional(preview["notional"]))
    except (HTTPException,AlpacaPaperUnavailable,MarketUnavailable,InvalidOperation):
        await db.alpaca_paper_manual_orders.update_one({"_id":cid},
            {"$set":{"state":"REJECTED_PREFLIGHT"}})
        await db.alpaca_paper_inflight.delete_one({"_id":user["id"],"client_order_id":cid})
        raise HTTPException(422,"Paper preflight changed; order not sent")
    await db.alpaca_paper_manual_orders.update_one({"_id":cid},
        {"$set":{"state":"SUBMITTING"}})
    try:
        result=await submit_stock_paper_buy(key,secret,symbol=preview["symbol"],
                     notional=preview["notional"],client_order_id=cid)
        if not isinstance(result,dict) or result.get("client_order_id")!=cid:
            raise AlpacaPaperUnavailable("Broker order identity mismatch")
        state=result.get("status","UNKNOWN")
        await db.alpaca_paper_manual_orders.update_one({"_id":cid},
            {"$set":{"state":"BROKER_REPORTED","broker_status":state,
                     "broker_id":result.get("id"),"filled_qty":result.get("filled_qty"),
                     "filled_avg_price":result.get("filled_avg_price")}})
    except (AlpacaPaperUnavailable,ValueError,TypeError):
        await db.alpaca_paper_manual_orders.update_one({"_id":cid},
            {"$set":{"state":"UNKNOWN","reason":"Broker response ambiguous; reconcile, never retry"}})
        raise HTTPException(503,{"message":"Broker result uncertain; do not resubmit",
                                 "client_order_id":cid})
    # Keep one-inflight lock until broker reaches a terminal state
    # (other than accepted/new/pending/partially filled).
    if state in ("filled","canceled","expired","rejected","done_for_day"):
        await db.alpaca_paper_inflight.delete_one({"_id":user["id"],"client_order_id":cid})
    return {"paper":True,"client_order_id":cid,"broker_status":state,
            "order_sent_to_paper_broker":True,"live":False,"ai_order":False}


@router.post("/orders/reconcile")
async def paper_reconcile(req:ReconcileReq,user:dict=Depends(get_current_user)):
    key,secret=await guard(user,reconciliation=True)
    row=await db.alpaca_paper_manual_orders.find_one({"_id":req.client_order_id,
                                                       "user_id":user["id"]})
    if not row:raise HTTPException(404,"No KAOS-owned paper order")
    try: result=await lookup_paper_order(key,secret,req.client_order_id)
    except AlpacaPaperUnavailable as exc:
        raise HTTPException(503,"Broker reconciliation unavailable") from exc
    if result is None:
        return {"status":"UNKNOWN","client_order_id":req.client_order_id,
                "note":"Broker did not find order; do not resubmit automatically"}
    status=result.get("status","unknown")
    await db.alpaca_paper_manual_orders.update_one(
        {"_id":req.client_order_id},
        {"$set":{"state":"BROKER_REPORTED","broker_status":status,
                 "filled_qty":result.get("filled_qty"),
                 "filled_avg_price":result.get("filled_avg_price")}})
    if status in ("filled","canceled","expired","rejected","done_for_day"):
        await db.alpaca_paper_inflight.delete_one(
            {"_id":user["id"],"client_order_id":req.client_order_id})
    return {"client_order_id":req.client_order_id,"paper":True,"broker_status":status,
            "filled_qty":result.get("filled_qty"),
            "filled_avg_price":result.get("filled_avg_price"),
            "execution_enabled_for_ai":False}


@router.get("/ai-paper-readiness")
async def alpaca_ai_paper_readiness(
    symbol:str="AAPL",user:dict=Depends(get_current_user)
):
    """Owner-only evaluation of recent stock forecasts against paper gates.

    Deliberately returns no order intent or automatic paper-trade permission.
    """
    from kaos_ai_alpaca_readiness import review_signal
    if not SYMBOL.fullmatch(symbol.upper()):
        raise HTTPException(422,"Only US equity tickers supported")
    # Does not need API keys or a currently open market to explain blocks.
    owner=os.getenv("KAOS_CANDLE_OWNER_USER_ID","")
    if not owner or user.get("id")!=owner or user.get("role") not in ("admin","super_admin"):
        raise HTTPException(403,"Owner-only AI paper research")
    models=await db.kaos_r2_research_models.find(
        {"owner_id":user["id"],"symbol":symbol.upper(),
         "asset_class":{"$in":["stock","etf"]},
         "research_only":True,"execution_enabled":False},
        {"_id":0}).sort("created_at",-1).limit(10).to_list(length=10)
    lookup={m["id"]:m for m in models if isinstance(m.get("id"),str)}
    docs=await db.kaos_r2_shadow_predictions.find(
        {"symbol":symbol.upper(),"asset_class":{"$in":["stock","etf"]},
         "model_id":{"$in":list(lookup)}},
        {"_id":0}).sort("observed_ts",-1).limit(15).to_list(length=15)
    evaluations=[]
    for row in docs:
        model=lookup.get(row.get("model_id"))
        if not model:
            continue
        evaluations.append(review_signal(row,model))
    return {"symbol":symbol.upper(),
            "evaluations":evaluations,
            "checked":len(evaluations),
            "research_only":True,"paper_order_authorized":False,
            "ai_paper_execution_enabled":False,
            "note":"Shadow forecasts are not instructions to trade. All AI broker orders are blocked."}


@router.get("/research-review")
async def paper_ai_research_review(user:dict=Depends(get_current_user)):
    """Compare existing *manual* Alpaca paper orders to prior AI research.

    No submission or modification of paper/AI orders, no implied auto-trading.
    Only the configured KAOS research owner can see candidate predictions.
    """
    await guard(user,reconciliation=True)
    from kaos_ai_paper_review import review_manual_paper_orders
    from datetime import timedelta
    # Keep bounded and avoid repeatedly scanning all forecasts.
    orders=await db.alpaca_paper_manual_orders.find(
        {"user_id":user["id"],"broker":"alpaca_paper"},
        {"_id":0}).sort("created_at",-1).limit(50).to_list(length=50)
    symbols=sorted({r.get("symbol") for r in orders
                    if isinstance(r.get("symbol"),str)})
    model_ids=await db.kaos_r2_research_models.distinct(
        "id",{"owner_id":user["id"],"research_only":True,
              "execution_enabled":False,
              "asset_class":{"$in":["stock","etf"]}})
    predictions=[]
    if orders and symbols and model_ids:
        try:
            earliest=min(datetime.fromisoformat(o["created_at"].replace("Z","+00:00"))
                         for o in orders)
            latest=max(datetime.fromisoformat(o["created_at"].replace("Z","+00:00"))
                       for o in orders)
        except (ValueError,TypeError,KeyError) as exc:
            raise HTTPException(503,"Paper order timestamps cannot be audited") from exc
        if earliest.tzinfo is None or latest.tzinfo is None:
            raise HTTPException(503,"Paper order timestamps lack timezone")
        # Only owner-model forecasts, and only candles that closed before
        # a manual order; _forecast_ok does a per-row final temporal check.
        from_ms=int((earliest-timedelta(minutes=5)).timestamp()*1000)
        through_ms=int(latest.timestamp()*1000)
        predictions=await db.kaos_r2_shadow_predictions.find(
            {"model_id":{"$in":model_ids},
             "symbol":{"$in":symbols},
             "asset_class":{"$in":["stock","etf"]},
             "candle_end_ts":{"$gte":from_ms,"$lte":through_ms}},
            {"_id":0}).sort("candle_end_ts",-1).limit(1500).to_list(length=1500)
    return review_manual_paper_orders(orders,predictions,model_ids)


@router.get("/orders/kaos")
async def kaos_paper_orders(user:dict=Depends(get_current_user)):
    await guard(user,reconciliation=True)
    rows=await db.alpaca_paper_manual_orders.find(
        {"user_id":user["id"]},{"_id":0}).sort("created_at",-1).limit(30).to_list(length=30)
    return {"orders":rows,"paper_only":True,"ai_execution_enabled":False}
