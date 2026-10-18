import os
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "kaos_test")
from datetime import datetime, timezone
from routes_paper import build_snapshot

NOW = datetime(2026, 10, 18, tzinfo=timezone.utc)


def test_snapshot_counts_only_open_buys():
    orders = [{"state": "SUBMITTED", "side": "BUY", "quantity": "10"},
              {"state": "REJECTED", "side": "BUY", "quantity": "50"},
              {"state": "FILLED", "side": "BUY", "quantity": "5"}]
    s = build_snapshot(orders, "100", NOW, False)
    assert s.open_exposure == "15" and s.open_positions == 2 and s.available_quote_balance == "85"
    assert s.live_consent is False and s.account_authorized is False


def test_snapshot_carries_kill_switch():
    assert build_snapshot([], "100", NOW, True).emergency_stopped is True
