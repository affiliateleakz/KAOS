from kaos_ai_signal_audit import assess

def prediction(i,**override):
    row={"prediction_id":str(i),"issued_at":"2026-10-01T00:00:00Z",
        "outcome_at":"2026-10-01T00:01:00Z","simulated":False,
        "production_trained":True,"outcome_verified":True,"direction":"BUY",
        "outcome":"WIN","asset":"SPY","model_version":"v1"}
    row.update(override)
    return row

def test_only_verified_forward_outcomes_count():
    report=assess([prediction(1),prediction(2,outcome="LOSS"),
                   prediction(3,simulated=True),
                   prediction(4,outcome_verified=False),
                   prediction(5,outcome_at="2026-09-30T00:00:00Z")])
    assert report["groups"][0]["decisive_samples"]==2
    assert report["groups"][0]["win_rate_ex_ties"]==50
    assert report["groups"][0]["performance_validated"] is False
    assert report["execution_enabled"] is False

def test_duplicate_forecasts_are_excluded():
    report=assess([prediction(1),prediction(1)])
    assert report["groups"][0]["wins"]==1
    assert report["excluded"]["duplicate"]==1

def test_empty_is_not_misrepresented():
    assert assess([])["groups"]==[]
