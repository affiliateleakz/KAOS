from affiliate_reconciliation_report import incomplete_report

def test_audit_reports_incomplete_and_legacy_without_mutation():
    payments=[{"event_id":"pay_1","state":"completed"},{"event_id":"pay_2","state":"pending_entries"},{"event_id":"pay_old"}]
    reversals=[{"reversal_id":"rev_1","state":"completed"},{"reversal_id":"rev_2","state":"pending_entries"}]
    original=[dict(x) for x in payments+reversals]
    report=incomplete_report(payments,reversals)
    assert [(x["kind"],x["id"],x["state"]) for x in report["items"]]==[
        ("payment","pay_2","pending_entries"),("payment","pay_old","legacy_unverified"),
        ("reversal","rev_2","pending_entries")]
    assert payments+reversals==original

def test_audit_limits_large_reports():
    out=incomplete_report([{"event_id":str(i)} for i in range(10)],[],max_records=3)
    assert len(out["items"])==3 and out["truncated"] is True
