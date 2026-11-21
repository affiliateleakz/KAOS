"""Regression tests for owner-configured R2 research watchlists."""
import asyncio
import pytest
from kaos_r2_ai_universe import CATALOG, BASE_MARKETS, MAX_ENROLLED, validate_markets, selected_markets

def test_catalog_large_and_unique():
    assert len(CATALOG) >= 100
    assert len(CATALOG) <= MAX_ENROLLED
    assert len(CATALOG) == len(set(CATALOG))
    assert ("BTC-USD", "crypto") in CATALOG
    assert ("AAPL", "stock") in CATALOG

def test_validation_preserves_catalog_order_and_rejects_bad_markets():
    rows = [
        {"symbol": "BTC-USD", "asset_class": "crypto"},
        {"symbol": "AAPL", "asset_class": "stock"},
    ]
    result = validate_markets(rows)
    assert set(result) == {("BTC-USD", "crypto"), ("AAPL", "stock")}
    with pytest.raises(ValueError):
        validate_markets(rows + rows[:1])
    with pytest.raises(ValueError):
        validate_markets([{"symbol": "UNSUPPORTED-USD", "asset_class": "crypto"}])
    with pytest.raises(ValueError):
        validate_markets([])

def test_initial_config_defaults_to_existing_universe():
    class FakeCollection:
        async def find_one(self, query):
            assert query == {"_id": "owner"}
            return None
    class FakeDB:
        kaos_r2_ai_universe = FakeCollection()
    assert asyncio.run(selected_markets(FakeDB())) == list(BASE_MARKETS)

def test_selected_config_never_expands_outside_catalog():
    class FakeCollection:
        async def find_one(self, query):
            return {"markets": [["BTC-USD", "crypto"],
                                ["FAKE", "stock"],
                                ["AAPL", "stock"]]}
    class FakeDB:
        kaos_r2_ai_universe = FakeCollection()
    assert set(asyncio.run(selected_markets(FakeDB()))) == {
        ("BTC-USD", "crypto"), ("AAPL", "stock")}
