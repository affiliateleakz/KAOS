from datetime import datetime, timezone, timedelta
from kaos_news_catalysts import aggregate_headlines

NOW = datetime(2026,10,19,tzinfo=timezone.utc)
def headline(score=0.5, **kwargs):
    return dict({"ticker":"SPY","headline":"Earnings beat expectations",
                 "source_url":"https://example.org/news/1",
                 "published_at":NOW,"score":score}, **kwargs)

def test_empty_no_division_by_zero():
    r=aggregate_headlines("SPY",[],now=NOW)
    assert r["sentiment_mean"] is None and r["executable"] is False

def test_invalid_and_stale_scores_excluded():
    rows=[headline(), headline(),headline(score=2),
          headline(score=float("nan")),
          headline(published_at=NOW-timedelta(days=2))]
    r=aggregate_headlines("SPY",rows,now=NOW)
    assert r["sample_count"] == 1
    assert r["sentiment_mean"] == 0.5
    assert r["excluded_count"] == 4

def test_valid_negative_news_remains_context_only():
    r=aggregate_headlines("SPY",[headline(score=-0.7)],now=NOW)
    assert r["sentiment_mean"] == -0.7
    assert r["status"] == "CONTEXT_ONLY"
    assert not r["executable"]


def test_multimodel_scores_do_not_overweight_one_story():
    observations = [
        headline(score=1.0, model_id="a", model_version="1"),
        headline(score=1.0, model_id="b", model_version="1"),
        headline(score=-1.0, headline="Company cuts guidance",
                 source_url="https://example.org/news/2",
                 model_id="a", model_version="1"),
    ]
    result = aggregate_headlines("SPY", observations, now=NOW)
    assert result["sample_count"] == 3
    assert result["distinct_stories"] == 2
    assert result["sentiment_mean"] == 0.0
