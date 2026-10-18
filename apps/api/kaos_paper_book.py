"""Simulated paper position book. Average-cost long-only accounting over a user's paper orders.

Fills are simulated at the caller-supplied quote price; nothing here is a market fill.
"""
from decimal import Decimal, ROUND_DOWN

ZERO = Decimal("0")
UNIT = Decimal("0.000000000001")
OPEN_STATES = {"SUBMITTED", "PARTIALLY_FILLED", "FILLED"}


def base_units(notional, price):
    return (Decimal(str(notional)) / Decimal(str(price))).quantize(UNIT, rounding=ROUND_DOWN)


def _units(order):
    if order.get("base_qty"):
        return Decimal(order["base_qty"])
    price = order.get("fill_price") or order.get("quote_price")
    return base_units(order["quantity"], price) if price else ZERO


def build_book(orders, starting_balance, today=None):
    """Replay accepted orders oldest-first into positions, realized P&L and cash."""
    positions, realized, realized_today = {}, ZERO, ZERO
    for o in sorted(orders, key=lambda o: o.get("created_at", "")):
        if o.get("state") not in OPEN_STATES:
            continue
        p = positions.setdefault(o["symbol"], {"symbol": o["symbol"], "asset_class": o.get("asset_class", "CRYPTO_SPOT"),
                                               "units": ZERO, "cost": ZERO, "realized": ZERO})
        notional, units = Decimal(o["quantity"]), _units(o)
        if o.get("side") == "BUY":
            p["units"] += units
            p["cost"] += notional
            p["asset_class"] = o.get("asset_class", p["asset_class"])
            continue
        if p["units"] <= 0:
            continue
        units = min(units, p["units"])
        cost_out = p["cost"] if units == p["units"] else p["cost"] * units / p["units"]
        pnl = notional - cost_out
        p["units"] -= units
        p["cost"] -= cost_out
        p["realized"] += pnl
        realized += pnl
        if today and o.get("created_at", "").startswith(today):
            realized_today += pnl
    open_positions = [p for p in positions.values() if p["units"] > 0]
    open_cost = sum((p["cost"] for p in open_positions), ZERO)
    cash = Decimal(str(starting_balance)) + realized - open_cost
    return {"positions": positions, "open": open_positions, "realized": realized,
            "realized_today": realized_today, "open_cost": open_cost, "cash": cash,
            "starting_balance": Decimal(str(starting_balance))}


def money(d):
    return format(Decimal(d).quantize(Decimal("0.01")), "f")


def _price(d):
    return format(d.quantize(Decimal("0.01") if d >= 1 else Decimal("0.00000001")), "f")


def book_view(book):
    return {
        "starting_balance": money(book["starting_balance"]), "cash": money(book["cash"]),
        "open_cost": money(book["open_cost"]), "realized_pnl": money(book["realized"]),
        "positions": [{"symbol": p["symbol"], "asset_class": p["asset_class"], "units": format(p["units"].normalize(), "f"),
                       "cost": money(p["cost"]), "avg_price": _price(p["cost"] / p["units"]),
                       "realized_pnl": money(p["realized"])} for p in book["open"]],
    }
