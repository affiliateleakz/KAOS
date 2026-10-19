from catalyst_learning_rows import make_catalyst_example

def test_catalyst_rows_contain_only_known_evidence():
    entry={"symbol":"SPY","source":"equity_sip","asset_class":"stock",
           "observed_at":"2026-10-18T12:00:00Z","bid":"100","ask":"100.02"}
    exit_quote={**entry,"observed_at":"2026-10-18T12:00:15Z","bid":"100.40","ask":"100.42"}
    evidence=[
        {"asset":"SPY","source":"news","event_id":"known",
         "published_at":"2026-10-18T11:58:00Z","first_received_at":"2026-10-18T11:59:00Z"},
        {"asset":"SPY","source":"news","event_id":"future",
         "published_at":"2026-10-18T11:58:00Z","first_received_at":"2026-10-18T12:00:01Z"},
    ]
    row=make_catalyst_example(entry,exit_quote,15,evidence)
    assert row["buy_profitable"] is True
    assert [v["event_id"] for v in row["available_events"]]==["known"]
    assert row["research_only"] is True
