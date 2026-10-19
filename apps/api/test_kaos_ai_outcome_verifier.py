import pytest
from kaos_ai_outcome_verifier import verify

def data():
    p={"timestamp":"2026-10-18T12:00:00Z","prediction":"BUY","asset":"BTC-USD","simulated":False,"productionTrained":True}
    a={"observed_at":"2026-10-18T12:00:01Z","asset":"BTC-USD","source":"coinbase","price":"100"}
    b={"observed_at":"2026-10-18T12:00:31Z","asset":"BTC-USD","source":"coinbase","price":"101"}
    return p,a,b

def test_verified_win():
    p,a,b=data()
    assert verify(p,a,b,30)["outcome"]=="WIN"

def test_wrong_market_refused():
    p,a,b=data();b["asset"]="ETH-USD"
    with pytest.raises(ValueError,match="Asset"):verify(p,a,b,30)

def test_simulated_rejected():
    p,a,b=data();p["simulated"]=True
    with pytest.raises(ValueError,match="Untrained"):verify(p,a,b,30)

def test_stale_outcome_rejected():
    p,a,b=data();b["observed_at"]="2026-10-18T12:05:00Z"
    with pytest.raises(ValueError,match="timestamps"):verify(p,a,b,30)
