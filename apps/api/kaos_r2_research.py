"""R2 historical research utilities. No broker calls, models, or training side effects."""
from kaos_structure_replay import replay

# A 1-minute, five-minute, or fifteen-minute archive can be irregular because
# stock exchanges close and data providers may omit zero-volume minutes.
# Never fabricate bars or silently choose only a favorable contiguous interval.
def inspect_history(rows, seconds):
    if not isinstance(rows, list):
        raise ValueError("Expected archived candles")
    if seconds not in (60, 300, 900):
        raise ValueError("Unsupported archive interval")
    if not rows:
        return {"bars": 0, "gap_count": 0, "missing_intervals": 0,
                "first_ts": None, "last_ts": None, "contiguous": False}
    interval = seconds * 1000
    times = [r["ts"] for r in rows]
    gaps = 0
    missing = 0
    for a, b in zip(times, times[1:]):
        delta = b - a
        if delta <= 0 or delta % interval:
            raise ValueError("Non-increasing or unaligned archive timestamps")
        if delta > interval:
            gaps += 1
            missing += delta // interval - 1
    return {"bars": len(times), "gap_count": gaps, "missing_intervals": missing,
            "first_ts": times[0], "last_ts": times[-1], "contiguous": gaps == 0}

def structure_replay_from_archive(rows, seconds, *, expiry_bars=4, lookback=12):
    diag = inspect_history(rows, seconds)
    # A minimum number of completed, gap-free candles is required for a valid
    # replay. Reject, rather than return biased statistics from partial slices.
    min_bars = lookback + expiry_bars + 5
    if not diag["contiguous"] or diag["bars"] < min_bars:
        return {"status": "insufficient_contiguous_history",
                "history": diag, "minimum_bars": min_bars,
                "research_only": True, "execution_enabled": False,
                "performance": None,
                "message": "Archive contains gaps or too few bars; no backtest was run"}
    result = replay(rows, expiry_bars=expiry_bars, lookback=lookback)
    return {"status": "completed", "history": diag, "research_only": True,
            "execution_enabled": False, **result}
