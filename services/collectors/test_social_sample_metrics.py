"""Research-only machine-readable public Bluesky sample metrics."""
from datetime import datetime, timezone, timedelta
from bluesky_search import summarize_search
from bluesky_social import observe_accounts


NOW = datetime(2026, 11, 20, 5, 0, tzinfo=timezone.utc)


def search_post(uri_id, minutes_ago, author):
    ts = (NOW - timedelta(minutes=minutes_ago)).isoformat()
    return {"uri": f"at://did:plc:{author}/app.bsky.feed.post/{uri_id}",
            "record": {"text": "$AAPL looks interesting", "createdAt": ts},
            "indexedAt": ts,
            "author": {"did": f"did:plc:{author}", "handle": f"{author}.bsky.social"}}


def test_search_includes_structured_current_prior_counts():
    posts = [
        search_post("a1", 10, "alice"), search_post("a2", 20, "alice"),
        search_post("b1", 35, "bob"), search_post("c1", 80, "carol"),
        search_post("a1", 10, "alice"),
    ]
    observation = summarize_search("AAPL", posts, now=NOW)
    metrics = observation["sample_metrics"]
    assert metrics["sampled_posts"] == 3
    assert metrics["sampled_unique_authors"] == 2
    assert metrics["previous_hour_posts"] == 1
    assert metrics["previous_hour_unique_authors"] == 1
    assert metrics["coverage"] == "bounded_search_sample_not_platform_total"


def test_monitored_accounts_include_machine_readable_unique_authors():
    def feed_item(post_id, handle):
        ts = (NOW - timedelta(minutes=4)).isoformat()
        return {"post": {
            "uri": f"at://did:plc:{handle}/app.bsky.feed.post/{post_id}",
            "indexedAt": ts,
            "record": {"text": "$AAPL #stocks", "createdAt": ts},
            "author": {"handle": handle, "did": f"did:plc:{handle}"},
        }}
    items = observe_accounts(
        {"alice.bsky.social": [feed_item("a1", "alice.bsky.social"),
                                feed_item("a2", "alice.bsky.social")],
         "bob.bsky.social": [feed_item("b1", "bob.bsky.social")]},
        ["AAPL"], now=NOW,
    )
    assert len(items) == 1
    metrics = items[0]["sample_metrics"]
    assert metrics["sampled_posts"] == 3
    assert metrics["sampled_unique_authors"] == 2
    assert metrics["previous_hour_posts"] is None
    assert metrics["coverage"] == "bounded_monitored_accounts_not_platform_total"
