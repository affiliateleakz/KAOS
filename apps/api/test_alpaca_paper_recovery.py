"""Alpaca paper order recovery must never cause order retries or false P&L."""
from datetime import datetime,timezone
import pytest
from alpaca_paper_recovery import classify,risk_ledger_status

NOW=datetime(2026,11,21,tzinfo=timezone.utc)
KAOS_ORDER={"client_order_id":"kaos-paper-"+"a"*32,"state":"UNKNOWN"}

def test_missing_broker_order_remains_locked():
    result=classify(KAOS_ORDER,None,now=NOW)
    assert result["broker_status"]=="UNKNOWN_NOT_FOUND"
    assert result["retain_inflight_lock"] is True
    assert result["can_submit_again_automatically"] is False

@pytest.mark.parametrize("status",["accepted","pending_new","new","partially_filled","pending_cancel","held"])
def test_active_broker_order_keeps_lock(status):
    result=classify(KAOS_ORDER,{"client_order_id":KAOS_ORDER["client_order_id"],"status":status},now=NOW)
    assert result["retain_inflight_lock"] is True
    assert not result["terminal"]

@pytest.mark.parametrize("status",["filled","canceled","rejected","expired","done_for_day"])
def test_terminal_reconciliation_may_release_lock_but_never_auto_submit(status):
    result=classify(KAOS_ORDER,{"client_order_id":KAOS_ORDER["client_order_id"],"status":status},now=NOW)
    assert result["terminal"] is True
    assert result["retain_inflight_lock"] is False
    assert result["can_submit_again_automatically"] is False

def test_wrong_broker_order_identity_is_never_reconciled():
    with pytest.raises(ValueError):
        classify(KAOS_ORDER,{"client_order_id":"other","status":"filled"},now=NOW)

def test_unknown_broker_state_fails_closed():
    result=classify(KAOS_ORDER,{"client_order_id":KAOS_ORDER["client_order_id"],"status":"unexpected"},now=NOW)
    assert result["broker_status"]=="UNKNOWN_BROKER_STATUS"
    assert result["retain_inflight_lock"] is True

def test_account_equity_gain_does_not_count_as_realized_profit():
    result=risk_ledger_status({"equity":"1200","last_equity":"1000"})
    assert result["daily_realized_pnl"] is None
    assert result["fees_total"] is None
    assert result["realized_loss_limit_verified"] is False
    assert not result["paper_auto_execution_enabled"]
    assert "full_broker_fill_history_not_verified" in result["incomplete_requirements"]

def test_even_verified_inputs_need_independent_audit():
    result=risk_ledger_status({"equity":"600","last_equity":"700"},
        fill_pages_complete=True,fees_reconciled=True,basis_reconciled=True)
    assert result["realized_loss_limit_verified"] is False
    assert result["daily_realized_pnl"] is None
