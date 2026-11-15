"""Local VADER text monitoring. Sentiment is not a directional trading prediction."""
from functools import lru_cache


@lru_cache(maxsize=1)
def analyzer():
    # Lazy import keeps unrelated API/login routes usable if deployment omitted
    # the new dependency. No downloads or remote sentiment service at runtime.
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    return SentimentIntensityAnalyzer()


@lru_cache(maxsize=2048)
def text_score(text):
    return analyzer().polarity_scores(str(text)[:1200])['compound']


def summarize(rows):
    output={}
    for source in ('news','social'):
        matching=[r for r in rows if r.get('source')==source]
        scores=[text_score(str(r.get('summary',''))) for r in matching]
        output[source]={'samples':len(scores),'score':sum(scores)/len(scores) if scores else None,
                        'bullish':sum(v>=.05 for v in scores),'bearish':sum(v<=-.05 for v in scores),
                        'neutral':sum(-.05<v<.05 for v in scores)}
    return {'method':'Local VADER 3.3.2; English lexical sentiment, not a trained financial language model',
            'window':'News/social published within 24 hours; bounded samples, not total mentions',
            'sources':output}
