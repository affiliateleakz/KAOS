"""Read-only status report for incomplete affiliate financial journal operations.

Never changes balances, payouts, membership access, or a financial record.
Use to identify records that require operator review and reconciliation.
"""
from datetime import datetime, timezone

def incomplete_report(payments, reversals, *, max_records=1000):
    if type(max_records) is not int or not 1 <= max_records <= 10000:
        raise ValueError("Invalid record cap")
    flagged=[]
    for kind, collection, id_field in (
        ("payment", payments, "event_id"),
        ("reversal", reversals, "reversal_id"),
    ):
        for document in collection:
            if not isinstance(document,dict):
                continue
            status=document.get("state")
            if status in ("completed",):
                continue
            flagged.append({"kind":kind,"id":str(document.get(id_field,"")),
                            "state":str(status) if status is not None else "legacy_unverified"})
            if len(flagged)>=max_records:
                return {"items":flagged,"truncated":True,"research_only":True}
    return {"items":flagged,"truncated":False,"research_only":True}
