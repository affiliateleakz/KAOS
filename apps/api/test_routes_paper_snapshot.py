import os
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "kaos_test")
from datetime import datetime, timezone
from routes_paper import build_snapshot
from kaos_paper_book import build_book

NOW = datetime(2026, 10, 18, tzinfo=timezone.utc)


def test_snapshot_counts_open_positions_and_cost():
    orders = [{"symbol": "BTC-USD", "state": "SUBMITTED", "side": "BUY", "quantity": "10", "quote_price": "100"},
              {"symbol": "ETH-USD", "state": "REJECTED", "side": "BUY", "quantity": "50", "quote_price": "10"},
              {"symbol": "ETH-USD", "state": "FILLED", "side": "BUY", "quantity": "5", "quote_price": "10"}]
    s = build_snapshot(build_book(orders, 100), "100", NOW, False)
    assert s.open_exposure == "15" and s.open_positions == 2 and s.available_quote_balance == "85"
    assert s.live_consent is False and s.account_authorized is False


def test_snapshot_carries_kill_switch():
    assert build_snapshot(build_book([], 100), "100", NOW, True).emergency_stopped is True
