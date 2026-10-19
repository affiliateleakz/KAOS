"""Research-only helpers to verify archived candle observations."""
from kaos_ai_outcome_verifier import verify

def verify_from_candles(prediction, entry, exit, horizon):
    return verify(prediction, entry, exit, horizon)
