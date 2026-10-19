"""Convert existing KAOS intelligence observations to point-in-time features.

Historical ingestion cannot retroactively prove original receipt. Only use
observations with a recorded first-received timestamp; otherwise reject.
"""
from datetime import datetime, timezone, timedelta
from multi_horizon_dataset import instant

ALLOWED_KINDS = {
    "news", "sec", "insider", "institutional", "social",
    "options_activity", "short_interest", "economic", "whale",
}

def normalize_event(row, *, symbol):
    """Return an as-known event with no directional trading authority."""
    if not isinstance(row, dict) or row.get("asset") != symbol:
        return None
    kind = str(row.get("kind") or row.get("source") or "").lower()
    if kind not in ALLOWED_KINDS:
        return None
    source = row.get("source")
    event_id = row.get("event_id")
    if not isinstance(source, str) or not source or not isinstance(event_id, str) or not event_id:
        return None
    published_at = row.get("published_at")
    received_at = row.get("first_received_at") or row.get("received_at")
    if published_at is None or received_at is None:
        return None
    try:
        publish = instant(published_at + "T00:00:00+00:00") if kind == "short_interest" and isinstance(published_at, str) and len(published_at) == 10 else instant(published_at)
        receive = instant(received_at)
    except (TypeError, ValueError, OverflowError):
        return None
    if publish > receive:
        return None
    # Date-only short-interest publications do not establish availability
    # at midnight. If hour is unknown, defer to the following UTC day.
    if kind == "short_interest" and isinstance(published_at, str) and len(published_at) == 10:
        publish += 86400
    available = max(publish, receive)
    return {
        "event_id": event_id, "kind": kind, "source": source,
        "published_at": datetime.fromtimestamp(publish, timezone.utc).isoformat(),
        "received_at": datetime.fromtimestamp(available, timezone.utc).isoformat(),
    }

def snapshot_events(observations, *, symbol, decision_at):
    """Deduplicate by source/event id and include only evidence already available."""
    cutoff = instant(decision_at)
    result = {}
    for row in observations:
        event = normalize_event(row, symbol=symbol)
        if event is None or instant(event["received_at"]) > cutoff:
            continue
        key = (event["source"], event["event_id"])
        if key not in result or instant(event["received_at"]) < instant(result[key]["received_at"]):
            result[key] = event
    return [result[key] for key in sorted(result)]
