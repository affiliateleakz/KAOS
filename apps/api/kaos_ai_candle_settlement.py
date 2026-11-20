"""Research-only bridge between closed archived candles and shadow outcomes."""
from datetime import datetime, timezone
from kaos_ai_outcome_verifier import verify, timestamp

def verify_from_candles(prediction, candles, horizon):
    """Use only matching market/source candles closing at forecast horizons."""
    asset, source, market = (prediction.get(k) for k in ("asset", "source", "asset_class"))
    if not all((asset, source, market)):
        raise ValueError("Missing forecast market provenance")
    issued = timestamp(prediction["timestamp"])
    result = []
    for target in (issued, issued + horizon):
        matched = []
        for bar in candles:
            if (bar.get("symbol"), bar.get("source"), bar.get("asset_class")) != (asset, source, market):
                continue
            seconds, opened = bar.get("seconds"), bar.get("ts")
            if type(seconds) is not int or seconds <= 0 or type(opened) is not int:
                continue
            closed = opened / 1000 + seconds
            if target <= closed <= target + 2:
                matched.append((closed, seconds, bar))
        if not matched:
            raise ValueError("No closed candle at required forecast boundary")
        matched.sort(key=lambda row: (row[0], row[1]))
        chosen_time = matched[0][0]
        prices = {str(row[2].get("close")) for row in matched if row[0] == chosen_time}
        if len(prices) != 1:
            raise ValueError("Conflicting settlement prices")
        result.append({"asset":asset, "source":source, "price":matched[0][2]["close"],
            "observed_at":datetime.fromtimestamp(chosen_time,timezone.utc).isoformat()})
    outcome = verify(prediction, result[0], result[1], horizon)
    return {**outcome, "verificationMethod":"closed_archived_candles",
            "verificationAssetClass":market, "verificationHorizonSeconds":horizon}
