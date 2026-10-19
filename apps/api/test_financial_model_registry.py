"""External model catalog must not imply live execution authorization."""
from kaos_financial_model_registry import MODELS, catalog, require_trading_validation


def test_all_requested_financial_model_families_listed():
    ids = {m.id for m in MODELS}
    assert {"fingpt", "trading_hero", "tiger_trading",
            "alphafin_stockgpt_stage1", "alphafin_stockgpt_stage2",
            "stockgpt_returns_research"} <= ids


def test_catalog_is_unconfigured_and_cannot_execute():
    rows = catalog()
    assert len(rows) == len(MODELS)
    assert all(row["status"] == "NOT_CONFIGURED" for row in rows)
    assert all(row["execution_authority"] is False for row in rows)


def test_validation_fail_closed():
    required = {"license_approved": True, "weights_verified": True,
                "holdout_passed": True, "paper_passed": True,
                "risk_approved": True, "operator_enabled": True}
    assert not require_trading_validation("fingpt", {})
    assert not require_trading_validation("unknown", required)
    for field in required:
        assert not require_trading_validation("fingpt", {**required, field: False})
    assert require_trading_validation("fingpt", required)
