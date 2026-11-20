from point_in_time_events import snapshot_events, normalize_event

def event(**changes):
    row={"asset":"SPY","source":"news","event_id":"n1",
         "published_at":"2026-10-18T12:00:00Z",
         "first_received_at":"2026-10-18T12:01:00Z"}
    row.update(changes)
    return row

def test_news_first_seen_after_decision_excluded():
    assert snapshot_events([event()],symbol="SPY",decision_at="2026-10-18T12:00:30Z")==[]
    assert len(snapshot_events([event()],symbol="SPY",decision_at="2026-10-18T12:01:01Z"))==1

def test_no_inferred_receipt_from_observed_at():
    row=event()
    del row["first_received_at"]
    row["observed_at"]="2026-10-18T12:01:00Z"
    assert normalize_event(row,symbol="SPY") is None

def test_cross_symbol_and_duplicate_removed():
    rows=[event(),event(),event(asset="QQQ",event_id="n2")]
    assert len(snapshot_events(rows,symbol="SPY",decision_at="2026-10-18T12:02:00Z"))==1

def test_short_interest_publication_date_cannot_be_used_same_day():
    item=event(source="short_interest",event_id="si1",
               published_at="2026-10-18",
               first_received_at="2026-10-18T12:00:00Z")
    assert snapshot_events([item],symbol="SPY",decision_at="2026-10-18T23:59:59Z")==[]
    assert len(snapshot_events([item],symbol="SPY",decision_at="2026-10-19T00:00:01Z"))==1

def test_revised_future_article_cannot_leak():
    row=event(published_at="2026-10-18T12:02:00Z")
    assert normalize_event(row,symbol="SPY") is None
