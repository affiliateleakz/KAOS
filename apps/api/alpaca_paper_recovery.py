"""Conservative Alpaca Paper broker-recovery status classifier.

An unconfirmed broker submission is never retried. A missing order is UNKNOWN,
not proof that the POST failed. An order remains locked until Alpaca confirms
a terminal outcome. No network calls or execution operations in this module.
"""
from datetime import datetime, timezone, timedelta

TERMINAL = frozenset({"filled", "canceled", "expired", "rejected", "done_for_day"})
ACTIVE = frozenset({
    "accepted", "accepted_for_bidding", "pending_new", "new",
    "partially_filled", "pending_cancel", "pending_replace", "calculated",
    "stopped", "suspended", "held"
})


def classify(order, broker_record, *, now=None):
    if not isinstance(order, dict) or not isinstance(order.get("client_order_id"),str):
        raise ValueError("Stored KAOS paper order identity required")
    if now is None:
        now = datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("UTC clock required")
    if broker_record is None:
        status="UNKNOWN_NOT_FOUND"
        unlock=False
        filled=None
        avg_price=None
    else:
        if not isinstance(broker_record,dict) or broker_record.get("client_order_id")!=order["client_order_id"]:
            raise ValueError("Broker client order ID mismatch")
        status=broker_record.get("status")
        if not isinstance(status,str) or status not in TERMINAL | ACTIVE:
            status="UNKNOWN_BROKER_STATUS"
        unlock=status in TERMINAL
        filled=broker_record.get("filled_qty")
        avg_price=broker_record.get("filled_avg_price")
    return {
        "client_order_id":order["client_order_id"],
        "broker_status":status,
        "terminal":bool(unlock),
        "retain_inflight_lock":not unlock,
        "filled_qty":filled,
        "filled_avg_price":avg_price,
        "can_submit_again_automatically":False,
        "source":"alpaca_paper_order_lookup",
        "reconciliation_checked_at":now.isoformat(),
        "research_only":True,
    }


def risk_ledger_status(account, *, fill_pages_complete=False,
                       fees_reconciled=False, basis_reconciled=False):
    """Expose why account equity delta cannot be called daily realized P&L."""
    if not isinstance(account,dict):
        raise ValueError("Broker account snapshot required")
    reasons=[]
    if not fill_pages_complete: reasons.append("full_broker_fill_history_not_verified")
    if not fees_reconciled: reasons.append("fees_and_corrections_not_reconciled")
    if not basis_reconciled: reasons.append("position_cost_basis_not_reconciled")
    # An account equity delta includes unrealized price movements, deposits,
    # distributions and fees; it MUST NOT be substituted for realized P&L.
    return {
        "schema":"kaos_alpaca_daily_risk_ledger_readiness_v1",
        "daily_realized_pnl":None,
        "unrealized_pnl":None,
        "fees_total":None,
        "broker_reported_equity":account.get("equity"),
        "broker_reported_last_equity":account.get("last_equity"),
        "realized_loss_limit_verified":False,
        "paper_auto_execution_enabled":False,
        "incomplete_requirements":reasons or ["independent_broker_risk_audit_required"],
        "note":"Paper account equity changes are not verified realized trading profits or losses.",
    }
