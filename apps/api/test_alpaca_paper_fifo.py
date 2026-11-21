"""No manufactured net-PnL or opening-cost-basis in Alpaca paper FIFO tests."""
import pytest
from alpaca_paper_fifo import reconstruct_fifo_gross

def fill(i,side,qty,price,symbol="AAPL",time=None):
    return {"id":f"activity-{i}","symbol":symbol,"side":side,
            "qty":str(qty),"price":str(price),
            "transaction_time":time or f"2026-11-20T18:{i:02d}:00Z"}

def test_basic_fifo_lots_are_gross_only():
    rows=[fill(1,"buy","2","100"),fill(2,"buy","1","110"),
          fill(3,"sell","2.5","120")]
    result=reconstruct_fifo_gross(rows,partial_history=False)
    assert result["gross_fifo_pnl_provisional"]=="45.0"
    assert result["symbol_summaries"][0]["remaining_fifo_qty"]=="0.5"
    assert result["daily_realized_net_pnl"] is None
    assert result["daily_loss_limit_verified"] is False
    assert result["opening_basis_verified"] is False

def test_descending_api_rows_are_reordered():
    rows=[fill(3,"sell","1","110"),fill(2,"buy","1","100")]
    result=reconstruct_fifo_gross(rows,partial_history=False)
    assert result["gross_fifo_pnl_provisional"]=="10"
    assert result["symbol_summaries"][0]["unpaired_sell_qty"]=="0"

def test_sell_without_prior_buy_is_flagged_as_unknown_inventory():
    rows=[fill(1,"sell","2","100"),fill(2,"buy","2","99")]
    result=reconstruct_fifo_gross(rows,partial_history=False)
    assert result["gross_fifo_pnl_provisional"]=="0"
    assert result["symbol_summaries"][0]["unpaired_sell_qty"]=="2"
    assert "unknown_opening_inventory_or_short_trades" in result["blockers"]

def test_short_sale_is_not_silently_treated_as_long_sale():
    rows=[fill(1,"sell_short","1","100"),fill(2,"buy_to_cover","1","90")]
    result=reconstruct_fifo_gross(rows,partial_history=False)
    assert result["gross_fifo_pnl_provisional"]=="0"
    assert "short_sale_cost_basis_not_supported" in result["blockers"]

def test_partial_history_always_unverified():
    result=reconstruct_fifo_gross([fill(1,"buy","1","10"),fill(2,"sell","1","11")],
                                  partial_history=True,rejected_records=1)
    assert "activity_history_window_incomplete" in result["blockers"]
    assert "invalid_or_unreadable_fill_records" in result["blockers"]
    assert result["daily_realized_net_pnl"] is None

def test_duplicates_nan_negative_and_bad_timestamps_fail_closed():
    row=fill(1,"buy","1","10")
    with pytest.raises(ValueError): reconstruct_fifo_gross([row,row])
    with pytest.raises(ValueError): reconstruct_fifo_gross([fill(1,"buy","NaN","10")])
    with pytest.raises(ValueError): reconstruct_fifo_gross([fill(1,"buy","1","-4")])
    with pytest.raises(ValueError): reconstruct_fifo_gross([fill(1,"buy","1","10",time="bad")])

def test_multi_symbol_does_not_cross_cost_basis():
    rows=[fill(1,"buy",1,10),fill(2,"buy",1,20,symbol="MSFT"),
          fill(3,"sell",1,15)]
    result=reconstruct_fifo_gross(rows,partial_history=False)
    a={s["symbol"]:s for s in result["symbol_summaries"]}
    assert a["AAPL"]["gross_fifo_pnl"]=="5"
    assert a["MSFT"]["remaining_fifo_qty"]=="1"
