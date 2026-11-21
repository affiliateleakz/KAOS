"""Bounded Alpaca PAPER fill activity audit.

Uses Alpaca's paper /v2/account/activities/FILL endpoint and page_token
cursor. Reports exact broker fill activities as audit data, not net trading
profit. A bounded scan is never represented as complete account history.
"""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse
import httpx

from alpaca_paper_client import PAPER_ORIGIN, _check_credentials, AlpacaPaperUnavailable

MAX_PAGES=5
PAGE_SIZE=100
FIELDS=("id","order_id","symbol","side","qty","price","transaction_time","type","activity_type")


def _positive_decimal(value):
    try:
        result=Decimal(str(value))
    except (InvalidOperation,ValueError,TypeError) as exc:
        raise ValueError("Invalid fill quantity or price") from exc
    if not result.is_finite() or result<=0:
        raise ValueError("Invalid fill quantity or price")
    return result


def _utc_time(value):
    try:
        d=datetime.fromisoformat(value.replace("Z","+00:00"))
    except (AttributeError,ValueError,TypeError) as exc:
        raise ValueError("Invalid fill timestamp") from exc
    if d.tzinfo is None:
        raise ValueError("Fill timestamp missing timezone")
    return d.astimezone(timezone.utc)


def normalize_fill(row):
    if not isinstance(row,dict) or row.get("activity_type")!="FILL":
        raise ValueError("Unsupported broker activity")
    if not isinstance(row.get("id"),str) or not row["id"]:
        raise ValueError("Missing fill ID")
    if not isinstance(row.get("order_id"),str) or not row["order_id"]:
        raise ValueError("Missing broker order ID")
    if not isinstance(row.get("symbol"),str) or not row["symbol"]:
        raise ValueError("Missing fill symbol")
    if row.get("side") not in ("buy","sell","sell_short","buy_to_cover"):
        raise ValueError("Unsupported fill side")
    qty=_positive_decimal(row.get("qty"))
    price=_positive_decimal(row.get("price"))
    time=_utc_time(row.get("transaction_time"))
    return {
        "id":row["id"],"order_id":row["order_id"],
        "symbol":row["symbol"],"side":row["side"],
        "qty":format(qty,"f"),"price":format(price,"f"),
        "notional":format(qty*price,"f"),
        "transaction_time":time.isoformat(),
        "activity_type":"FILL",
    }


async def fetch_broker_fills(key,secret,*,max_pages=MAX_PAGES):
    if not 1<=max_pages<=MAX_PAGES:
        raise ValueError("Invalid page bound")
    headers=_check_credentials(key,secret)
    seen=set()
    fill_rows=[]
    token=None
    has_more=False
    rejected=0
    for page in range(max_pages):
        params={"direction":"desc","page_size":PAGE_SIZE}
        if token:
            params["page_token"]=token
        try:
            async with httpx.AsyncClient(timeout=12,follow_redirects=False) as client:
                response=await client.get(
                    PAPER_ORIGIN+"/v2/account/activities/FILL",
                    params=params,headers=headers)
        except httpx.HTTPError as exc:
            raise AlpacaPaperUnavailable("Alpaca paper fill activity unavailable") from exc
        if response.status_code!=200:
            raise AlpacaPaperUnavailable("Alpaca paper fill activity rejected")
        try:
            data=response.json()
        except ValueError as exc:
            raise AlpacaPaperUnavailable("Invalid Alpaca paper activity response") from exc
        if not isinstance(data,list):
            raise AlpacaPaperUnavailable("Invalid Alpaca paper activity page")
        if len(data)>PAGE_SIZE:
            raise AlpacaPaperUnavailable("Broker activity page exceeds bound")
        for row in data:
            try:
                entry=normalize_fill(row)
            except ValueError:
                rejected+=1
                continue
            if entry["id"] not in seen:
                seen.add(entry["id"])
                fill_rows.append(entry)
        if len(data)<PAGE_SIZE:
            has_more=False
            break
        # Descending page cursor must be the last source row's ID.
        next_token=data[-1].get("id") if isinstance(data[-1],dict) else None
        if not isinstance(next_token,str) or not next_token or next_token==token:
            raise AlpacaPaperUnavailable("Alpaca activity pagination stalled")
        token=next_token
        has_more=True
    return {
        "fills":fill_rows,
        "records_returned":len(fill_rows),
        "rejected_records":rejected,
        "partial_history":bool(has_more),
        "max_pages":max_pages,
        "source":"alpaca_paper_account_activities",
        "auto_trading_authorized":False,
    }


def reconcile_kaos_fills(fills_response, kaos_orders):
    """Group actual activity records by known KAOS broker-order IDs only."""
    if not isinstance(fills_response,dict) or not isinstance(kaos_orders,list):
        raise ValueError("Invalid fill audit inputs")
    broker_to_kaos={}
    for order in kaos_orders:
        if not isinstance(order,dict) or order.get("broker")!="alpaca_paper":
            continue
        broker_id=order.get("broker_id")
        if isinstance(broker_id,str) and broker_id:
            broker_to_kaos[broker_id]=order
    groups={}
    unmatched=0
    for fill in fills_response.get("fills",[]):
        order=broker_to_kaos.get(fill["order_id"])
        if not order:
            unmatched+=1
            continue
        key=order["client_order_id"]
        entry=groups.setdefault(key,{"client_order_id":key,"symbol":order["symbol"],
            "broker_order_id":fill["order_id"],"fills":0,
            "filled_qty":Decimal(0),"gross_buy_notional":Decimal(0),
            "gross_sell_notional":Decimal(0)})
        qty=_positive_decimal(fill["qty"])
        notional=_positive_decimal(fill["price"])*qty
        entry["fills"]+=1
        entry["filled_qty"]+=qty
        if fill["side"] in ("buy","buy_to_cover"):
            entry["gross_buy_notional"]+=notional
        else:
            entry["gross_sell_notional"]+=notional
    out=[]
    for entry in groups.values():
        out.append({
            **{k:v for k,v in entry.items() if not isinstance(v,Decimal)},
            "filled_qty":format(entry["filled_qty"],"f"),
            "gross_buy_notional":format(entry["gross_buy_notional"],"f"),
            "gross_sell_notional":format(entry["gross_sell_notional"],"f"),
            "realized_pnl":None,
        })
    out.sort(key=lambda row:row["client_order_id"])
    return {
        "schema":"kaos_alpaca_paper_fill_audit_v1",
        "matched_orders":len(out),"matched_fills":sum(x["fills"] for x in out),
        "unmatched_broker_fills":unmatched,"rows":out,
        "partial_history":fills_response.get("partial_history",True),
        "rejected_records":fills_response.get("rejected_records",0),
        "realized_pnl_verified":False,"fees_reconciled":False,
        "initial_cost_basis_verified":False,
        "daily_loss_limit_verified":False,
        "auto_paper_execution_enabled":False,
        "note":"Gross fill cash flows are NOT realized profit. Fill history may be partial; "
               "fees, opening inventory and corporate actions are not reconciled."
    }
