import asyncio
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
import services_trading as trading
import routes_opportunity as opportunity
import routes_billing as billing


@pytest.mark.parametrize(
    "tier,status,expected",
    [("pro", "ACTIVE", False), ("pro", "TRIAL", False), ("ultimate", "ACTIVE", True)],
)
def test_ai_signals_separate_from_general_insights_and_training(
    monkeypatch, tier, status, expected
):
    monkeypatch.setattr(
        billing, "get_plans", AsyncMock(return_value=billing.DEFAULT_PLANS)
    )
    monkeypatch.setattr(
        trading, "apply_ai_execution_lock", AsyncMock(side_effect=lambda ent: ent)
    )
    from datetime import datetime, timezone, timedelta

    ent = asyncio.run(
        trading.get_entitlements(
            {
                "membership_plan": tier,
                "membership_status": status,
                "membership_expires_at": (
                    datetime.now(timezone.utc) + timedelta(days=7)
                ).isoformat(),
            }
        )
    )
    assert ent["aiSignals"] is expected
    assert ent["aiInsights"] and ent["aiTraining"]
    monkeypatch.setattr(opportunity, "get_entitlements", AsyncMock(return_value=ent))
    if expected:
        assert asyncio.run(opportunity.signal_member({"id": "u"})) == {"id": "u"}
    else:
        with pytest.raises(HTTPException) as exc:
            asyncio.run(opportunity.signal_member({"id": "u"}))
        assert exc.value.status_code == 403
