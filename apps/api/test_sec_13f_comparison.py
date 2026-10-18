import pytest
from sec_13f_comparison import compare_holdings

def row(cusip,shares):
    return {"cusip":cusip,"issuer":"Example","reported_shares_or_principal":shares}

def test_reported_position_changes_are_not_trades():
    changes=compare_holdings([row("111111111","100"),row("222222222","40")],
                              [row("111111111","150"),row("333333333","20")])
    assert [(r["change"],r["net_reported_change"]) for r in changes]==[
        ("increase","50"),("decrease","-40"),("increase","20")]
    assert all(r["interpretation"]=="quarterly_holdings_difference_not_confirmed_trade" for r in changes)

def test_identical_snapshots_no_changes():
    assert compare_holdings([row("111111111","100")],[row("111111111","100")])==[]

def test_duplicate_cusip_rejected():
    with pytest.raises(ValueError,match="Duplicate"):
        compare_holdings([row("111111111","100"),row("111111111","200")],[])
