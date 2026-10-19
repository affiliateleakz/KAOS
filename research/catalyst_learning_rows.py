"""Compose source-vetted catalyst snapshots with quote-based learning labels.

This module does not train models or issue orders.
"""
from multi_horizon_dataset import make_example
from point_in_time_events import snapshot_events

def make_catalyst_example(entry, exit_quote, horizon_seconds, observations=(), **kwargs):
    if not entry.get("symbol"):
        raise ValueError("Missing instrument symbol")
    known = snapshot_events(
        observations, symbol=entry["symbol"], decision_at=entry["observed_at"]
    )
    return make_example(entry, exit_quote, horizon_seconds, events=known, **kwargs)
