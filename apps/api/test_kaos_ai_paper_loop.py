"""Experimental KAOS paper AI unit tests; no broker connectivity."""
from kaos_ai_paper_loop import settle_prediction, probability, BARS_MS

def test_up_paper_settlement_friction_and_label():
    p={"entry_price":100,"notional_usd":10,"direction":"UP"}
    s=settle_prediction(p,102,123456)
    assert s["state"]=="settled"
    assert s["correct_direction"] is True
    assert s["gross_pnl_usd"]==0.2
    assert s["net_pnl_usd"]<s["gross_pnl_usd"]

def test_down_direction_and_flat_moves():
    p={"entry_price":100,"notional_usd":10,"direction":"DOWN"}
    assert settle_prediction(p,98,1000)["correct_direction"] is True
    s=settle_prediction(p,100,1000)
    assert s["correct_direction"] is False
    assert s["net_pnl_usd"]<0

def test_probability_rejects_missing_and_gapped_bars():
    rows=[{"ts":i*BARS_MS,"open":100,"high":101,"low":99,"close":100,"volume":1} for i in range(9)]
    model={"weights":[0]*8,"mean":[0]*8,"std":[1]*8,"bias":0}
    assert probability(rows,model)==0.5
    rows[-1]["ts"]+=BARS_MS
    assert probability(rows,model) is None
