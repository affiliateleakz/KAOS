"""StockGPT-inspired news catalyst aggregation for KAOS Market Intelligence.

Independent implementation of headline scoring aggregation. A text-model's
sentiment output is context only, never market validation or order authority.
No OpenAI key is read from disk and no external API requests occur here.
"""
from datetime import datetime, timezone, timedelta
from math import isfinite


def aggregate_headlines(ticker, observations, *, now=None, max_age_hours=24):
    """Use only timestamped attributed headlines for a ticker.

    Observations: {ticker, headline, source_url, published_at, score}.
    The score must be supplied by a separately audited inference provider.
    Duplicate stories and missing provenance are excluded.
    """
    now = now or datetime.now(timezone.utc)
    accepted, discarded, seen = [], [], set()
    for item in observations:
        headline = item.get("headline")
        url = item.get("source_url")
        published = item.get("published_at")
        raw = item.get("score")
        if item.get("ticker") != ticker or not isinstance(headline, str) or not headline.strip():
            discarded.append("invalid_ticker_or_headline")
            continue
        if not isinstance(url, str) or not url.startswith(("https://", "http://")):
            discarded.append("missing_source")
            continue
        if not isinstance(published, datetime) or published.tzinfo is None or not (
            now - timedelta(hours=max_age_hours) <= published <= now
        ):
            discarded.append("missing_or_stale_timestamp")
            continue
        if isinstance(raw, bool) or not isinstance(raw, (float, int)) or not isfinite(raw) or not -1 <= raw <= 1:
            discarded.append("invalid_sentiment")
            continue
        key = (headline.casefold().strip(), url, item.get("model_id"), item.get("model_version"))
        if key in seen:
            discarded.append("duplicate")
            continue
        seen.add(key)
        accepted.append({"headline": headline.strip(), "source_url": url,
                         "published_at": published.isoformat(), "score": float(raw),
                         "model_id": item.get("model_id"),
                         "model_version": item.get("model_version")})
    # Multiple models scoring one story are not independent news events.
    # Average per distinct story first, avoiding exaggerated influence from
    # stories evaluated by more models than others.
    stories = {}
    for item in accepted:
        story_id = (item["headline"].casefold(), item["source_url"])
        stories.setdefault(story_id, []).append(item["score"])
    story_means = [sum(scores) / len(scores) for scores in stories.values()]
    n = len(accepted)
    avg = sum(story_means) / len(story_means) if story_means else None
    return {"ticker": ticker, "sample_count": n, "distinct_stories": len(stories),
            "sentiment_mean": round(avg, 5) if avg is not None else None,
            "headline_scores": accepted, "excluded_count": len(discarded),
            "excluded_reasons": discarded, "status": "CONTEXT_ONLY" if n else "NO_VALID_HEADLINES",
            "executable": False}
