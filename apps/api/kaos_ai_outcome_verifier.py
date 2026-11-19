"""KAOS shadow outcome verification helpers; no trading authority."""
from decimal import Decimal
from datetime import datetime, timezone

def timestamp(value):
    if not isinstance(value, str):
        raise ValueError('Timestamp must be an ISO8601 string')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError('Timestamp requires an explicit timezone')
    return parsed.astimezone(timezone.utc).timestamp()

def verify(prediction, first, last, horizon):
    if prediction.get("simulated") or not prediction.get("productionTrained"):
        raise ValueError("Untrained or simulated forecast")
    direction=prediction.get("prediction")
    if direction not in ("BUY","SELL") or type(horizon) is not int or not 5<=horizon<=3600:
        raise ValueError("Invalid direction or horizon")
    if not first.get("source") or first["source"]!=last.get("source"):
        raise ValueError("Quote source mismatch")
    if not (prediction.get("asset")==first.get("asset")==last.get("asset")):
        raise ValueError("Asset mismatch")
    issued=timestamp(prediction["timestamp"])
    start=timestamp(first["observed_at"])
    finish=timestamp(last["observed_at"])
    if not (issued<=start<=issued+2 and issued+horizon<=finish<=issued+horizon+2):
        raise ValueError("Quote timestamps do not match horizon")
    a,b=Decimal(str(first["price"])),Decimal(str(last["price"]))
    if not all(x.is_finite() and x>0 for x in (a,b)):
        raise ValueError("Invalid observed price")
    outcome="TIE" if a==b else ("WIN" if (b>a)==(direction=="BUY") else "LOSS")
    return {"outcome":outcome,"outcomeVerified":True,"outcomeAt":last["observed_at"],
      "verificationSource":first["source"],"entryPrice":str(a),"exitPrice":str(b),
      "outcomeMode":"directional_only"}
