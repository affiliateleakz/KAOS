from datetime import datetime, timezone
from kaos_ai_candle_settlement import verify_from_candles
import pytest

def base():
    p={"timestamp":"2026-10-18T12:00:00Z","prediction":"BUY",
       "asset":"BTC-USD","source":"coinbase_exchange_public_candles",
       "asset_class":"crypto","simulated":False,"productionTrained":True}
    def bar(second,price):
        return {"symbol":"BTC-USD","source":p["source"],"asset_class":"crypto",
                "seconds":60,"ts":int(datetime(2026,10,18,12,second,tzinfo=timezone.utc).timestamp()*1000),
                "close":price}
    return p,[bar(0,"100"),bar(0,"101")]

def test_exact_close_boundaries():
    p,bars=base()
    p["timestamp"]="2026-10-18T12:01:00Z"
    bars[1]["ts"]=int(datetime(2026,10,18,12,1,tzinfo=timezone.utc).timestamp()*1000)
    assert verify_from_candles(p,bars,60)["outcome"]=="WIN"

def test_unavailable_intraminute_expiry():
    p,bars=base()
    with pytest.raises(ValueError,match="No closed candle"):
        verify_from_candles(p,bars,30)

def test_other_source_cannot_settle():
    p,bars=base()
    bars[0]["source"]="other-broker"
    with pytest.raises(ValueError,match="No closed candle"):
        verify_from_candles(p,bars,60)

def test_simulated_forecast_not_verified():
    p,bars=base()
    p["timestamp"]="2026-10-18T12:01:00Z"
    bars[1]["ts"]=int(datetime(2026,10,18,12,1,tzinfo=timezone.utc).timestamp()*1000)
    p["simulated"]=True
    with pytest.raises(ValueError,match="Untrained"):
        verify_from_candles(p,bars,60)
