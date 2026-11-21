"""Conservative FIFO closed-lot reconstruction from Alpaca PAPER FILL activities.

Demonstrates *gross* trade P&L within a bounded activity window, not verified
daily realized net P&L. Unknown opening inventory, missing pages, adjustments
or fees can invalidate any result. No execution path imports this module.
"""
from collections import defaultdict, deque
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import math

ZERO=Decimal("0")


def _decimal(value):
    try: result=Decimal(str(value))
    except (InvalidOperation,TypeError,ValueError) as exc:
        raise ValueError("Invalid fill quantity or price") from exc
    if not result.is_finite() or result<=ZERO:
        raise ValueError("Invalid fill quantity or price")
    return result


def _time(value):
    if not isinstance(value,str):
        raise ValueError("Missing fill timestamp")
    try: d=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError as exc: raise ValueError("Invalid timestamp") from exc
    if d.tzinfo is None: raise ValueError("Timezone missing")
    return d.astimezone(timezone.utc)


def reconstruct_fifo_gross(fill_rows, *, partial_history=True, rejected_records=0):
    if not isinstance(fill_rows,list) or len(fill_rows)>500:
        raise ValueError("Bounded fill array required")
    if not isinstance(rejected_records,int) or isinstance(rejected_records,bool) or rejected_records<0:
        raise ValueError("Invalid dropped-row count")
    rows=[]
    seen=set()
    for raw in fill_rows:
        if not isinstance(raw,dict):
            raise ValueError("Invalid fill")
        identity=raw.get("id")
        if not isinstance(identity,str) or not identity or identity in seen:
            raise ValueError("Missing/duplicate fill ID")
        seen.add(identity)
        symbol=raw.get("symbol")
        side=raw.get("side")
        if not isinstance(symbol,str) or not symbol or len(symbol)>32:
            raise ValueError("Invalid symbol")
        if side not in ("buy","sell","buy_to_cover","sell_short"):
            raise ValueError("Unknown side")
        rows.append({
            "id":identity,"symbol":symbol,"side":side,
            "time":_time(raw.get("transaction_time")),
            "qty":_decimal(raw.get("qty")),
            "price":_decimal(raw.get("price")),
        })
    rows.sort(key=lambda f:(f["time"],f["id"]))
    lots=defaultdict(deque)
    gross=defaultdict(lambda:ZERO)
    closed_qty=defaultdict(lambda:ZERO)
    unpaired=defaultdict(lambda:ZERO)
    short_sides=set()
    events=[]
    for fill in rows:
        symbol=fill["symbol"]
        side=fill["side"]
        qty=fill["qty"]
        if side in ("sell_short","buy_to_cover"):
            short_sides.add(symbol)
            unpaired[symbol]+=qty
            continue
        if side=="buy":
            lots[symbol].append([qty,fill["price"]])
            continue
        # Never infer a zero historical opening position. An unmatched SELL
        # could be closing inventory held before this bounded window.
        while qty>ZERO and lots[symbol]:
            lot=lots[symbol][0]
            take=min(qty,lot[0])
            profit=take*(fill["price"]-lot[1])
            gross[symbol]+=profit
            closed_qty[symbol]+=take
            events.append({
                "symbol":symbol,"closed_qty":str(take),
                "gross_pnl":str(profit),"time":fill["time"].isoformat(),
                "source":"paper_fill_fifo_reconstruction",
            })
            lot[0]-=take
            qty-=take
            if lot[0]==ZERO:lots[symbol].popleft()
        if qty>ZERO:
            unpaired[symbol]+=qty
    symbols=sorted(set(lots)|set(gross)|set(unpaired)|short_sides)
    records=[]
    for symbol in symbols:
        records.append({
            "symbol":symbol,
            "gross_fifo_pnl":str(gross[symbol]),
            "gross_closed_qty":str(closed_qty[symbol]),
            "unpaired_sell_qty":str(unpaired[symbol]),
            "remaining_fifo_qty":str(sum((lot[0] for lot in lots[symbol]),ZERO)),
            "short_or_cover_activity_seen":symbol in short_sides,
        })
    blockers=[]
    if partial_history:blockers.append("activity_history_window_incomplete")
    if rejected_records:blockers.append("invalid_or_unreadable_fill_records")
    if any(v>ZERO for v in unpaired.values()):
        blockers.append("unknown_opening_inventory_or_short_trades")
    if short_sides:blockers.append("short_sale_cost_basis_not_supported")
    blockers.extend([
        "opening_inventory_not_independently_verified",
        "broker_fees_and_adjustments_not_reconciled",
        "not_full_daily_realized_account_ledger",
    ])
    return {
        "schema":"kaos_alpaca_paper_fifo_gross_research_v1",
        "fills_replayed":len(rows),
        "closed_lot_events":events[-100:],
        "symbol_summaries":records,
        "gross_fifo_pnl_provisional":str(sum(gross.values(),ZERO)),
        "daily_realized_net_pnl":None,
        "daily_loss_limit_verified":False,
        "fees_reconciled":False,
        "opening_basis_verified":False,
        "execution_enabled":False,
        "research_only":True,
        "blockers":blockers,
        "note":"FIFO gross P&L is provisional, based only on bounded paper fills. It must not be displayed as verified daily realized net P&L."
    }
