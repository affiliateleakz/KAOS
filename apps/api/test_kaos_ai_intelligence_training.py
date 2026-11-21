"""Strict historical as-of joins for optional KAOS intelligence model."""
from datetime import datetime, timezone, timedelta
import math
import pytest
from kaos_ai_intelligence_training import (
    normalize_events,join_asof_samples,train_enriched,SCHEMA,FEATURE_NAMES
)

T0=1760000000000
START=datetime.fromtimestamp(T0/1000,timezone.utc)

def candle_rows(count=510):
    return [
        {"ts":T0+i*60000,
         "open":100+2*math.sin((i-1)/7)+i*.008,
         "close":100+2*math.sin(i/7)+i*.008,
         "high":105,"low":95,"volume":100+i%8}
        for i in range(count)
    ]

def event(i,*,source="news",observed_at=None,published_at=None,direction="bullish"):
    at=START+timedelta(minutes=5+i*7) if observed_at is None else observed_at
    published=at-timedelta(seconds=10) if published_at is None else published_at
    return {"asset":"AAPL","asset_class":"stock",
            "source":source,"event_id":f"{source}:{i}",
            "direction":direction,"strength":.65,
            "observed_at":at.isoformat(),"published_at":published.isoformat()}

def test_future_observation_is_not_retrospectively_in_training():
    rows=candle_rows()
    very_late=START+timedelta(days=12)
    records=normalize_events([event(1,observed_at=very_late,
                                    published_at=START)],"AAPL","stock")
    samples,stats=join_asof_samples(rows,records,60,4)
    assert stats["sample_coverage"]==0
    assert stats["distinct_matched_events"]==0
    assert all(all(x==0 for x in s["x"][8:]) for s in samples)

def test_historical_event_only_visible_after_both_publication_and_observation():
    rows=candle_rows()
    at=START+timedelta(minutes=100)
    records=normalize_events([event(1,observed_at=at,published_at=at-timedelta(seconds=1))],"AAPL","stock")
    samples,stats=join_asof_samples(rows,records,60,4)
    early=next(s for s in samples if s["ts"]==T0+50*60000)
    late=next(s for s in samples if s["ts"]==T0+105*60000)
    assert all(x==0 for x in early["x"][8:])
    assert any(x!=0 for x in late["x"][8:])
    assert stats["distinct_matched_events"]==1

def test_publication_after_observation_is_rejected():
    at=START+timedelta(minutes=20)
    bad=event(1,observed_at=at,published_at=at+timedelta(minutes=1))
    assert normalize_events([bad],"AAPL","stock")==[]

def test_neutral_news_headline_not_mislabeled_as_bullish_model_feature():
    rows=candle_rows()
    records=normalize_events([event(1,direction="neutral")],"AAPL","stock")
    assert records==[]
    outcome=train_enriched(rows,[event(1,direction="neutral")],
                           symbol="AAPL",asset_class="stock")
    assert outcome["status"]=="insufficient_external_history"

def test_missing_enriched_sources_never_claims_an_advanced_model():
    report=train_enriched(candle_rows(),[],symbol="AAPL",asset_class="stock")
    assert report["status"]=="insufficient_external_history"
    assert report["execution_enabled"] is False
    assert "model" not in report

def test_time_safe_multisource_model_stays_research_only():
    rows=candle_rows()
    events=[event(i,source="news" if i%2 else "social",
                  direction="bullish" if i%3 else "bearish")
            for i in range(65)]
    result=train_enriched(rows,events,symbol="AAPL",asset_class="stock")
    assert result["status"] in ("candidate_not_validated","validated_research_candidate")
    assert result["research_only"] is True
    assert result["execution_enabled"] is False
    assert result["model"]["schema"]==SCHEMA
    assert len(result["model"]["features"])==len(FEATURE_NAMES)
    assert set(result["source_categories_in_training"])=={"news","social"}
    assert result["coverage"]["distinct_matched_events"]>=20
    assert result["test"]["samples"]>=20

def test_malformed_strong_event_is_excluded():
    row=event(1);row["strength"]=float("nan")
    assert normalize_events([row],"AAPL","stock")==[]

def test_bounded_observation_limit_fails_closed():
    with pytest.raises(ValueError):
        normalize_events([event(i) for i in range(3001)],"AAPL","stock")
