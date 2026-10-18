from decimal import Decimal
from kaos_paper_book import build_book, book_view


def order(side, qty, price, at, symbol="BTC-USD", state="SUBMITTED", base=None):
    o = {"symbol": symbol, "side": side, "quantity": qty, "fill_price": price, "state": state, "created_at": at}
    if base:
        o["base_qty"] = base
    return o


def test_average_cost_partial_and_full_close():
    orders = [order("BUY", "10", "100", "2026-10-18T01"), order("BUY", "10", "200", "2026-10-18T02"),
              order("SELL", "15", "150", "2026-10-18T03", base="0.1"),
              order("SELL", "7.5", "150", "2026-10-18T04", base="0.05")]
    b = build_book(orders, 100, today="2026-10-18")
    # 0.15 units for $20 -> avg 133.33; sell 0.1 @150 = $15 vs cost 13.33
    assert b["open"] == [] and b["open_cost"] == 0
    assert round(b["realized"], 8) == Decimal("2.5")
    assert round(b["cash"], 8) == Decimal("102.5") and round(b["realized_today"], 8) == Decimal("2.5")


def test_rejected_orders_and_unheld_sells_are_ignored():
    orders = [order("BUY", "10", "100", "1", state="REJECTED"), order("SELL", "5", "100", "2", base="0.05")]
    b = build_book(orders, 100)
    assert b["open"] == [] and b["cash"] == 100 and b["realized"] == 0


def test_loss_and_view_formatting():
    b = build_book([order("BUY", "20", "50", "1"), order("BUY", "5", "1", "2", symbol="ETH-USD"),
                    order("SELL", "10", "25", "3", base="0.4")], 100)
    v = book_view(b)
    assert v["realized_pnl"] == "-10.00" and v["cash"] == "85.00" and v["open_cost"] == "5.00"
    assert v["positions"] == [{"symbol": "ETH-USD", "asset_class": "CRYPTO_SPOT", "units": "5", "cost": "5.00",
                               "avg_price": "1.00", "realized_pnl": "0.00"}]
