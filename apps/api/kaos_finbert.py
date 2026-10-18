"""KAOS FinBERT shadow sentiment. No order authorization, no trade signals.

Model is opt-in and loaded lazily; production must pre-cache pinned model files.
"""
import hashlib
import os
from datetime import datetime, timezone
from functools import lru_cache

MODEL = 'ProsusAI/finbert'

def parse_utc(value):
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    else:
        raise ValueError('timestamp required')
    if dt.tzinfo is None:
        raise ValueError('timestamp must have timezone')
    return dt.astimezone(timezone.utc)

@lru_cache(maxsize=1)
def load_model():
    if os.getenv('KAOS_FINBERT_ENABLED', 'disabled') != 'enabled':
        raise RuntimeError('FinBERT disabled')
    from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
    model_path = os.getenv('KAOS_FINBERT_MODEL_PATH')
    if not model_path:
        raise RuntimeError('KAOS_FINBERT_MODEL_PATH must point to a locally cached model')
    tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(model_path, local_files_only=True)
    return pipeline('text-classification', model=model, tokenizer=tokenizer, top_k=None, device=-1)

def normalize(scores):
    if isinstance(scores, list) and len(scores) == 1 and isinstance(scores[0], list):
        scores = scores[0]
    probabilities = {str(x['label']).lower(): float(x['score']) for x in scores}
    if set(probabilities) != {'positive', 'negative', 'neutral'}:
        raise ValueError('Unexpected model labels')
    if any(not (0 <= p <= 1) for p in probabilities.values()) or abs(sum(probabilities.values()) - 1) > .02:
        raise ValueError('Invalid model probabilities')
    return probabilities

def score_headline(headline, published_at, observed_at, market, predictor=None):
    if not isinstance(headline, str) or not headline.strip() or len(headline) > 2000:
        raise ValueError('headline must contain 1-2000 characters')
    if not isinstance(market, str) or not (1 <= len(market) <= 40):
        raise ValueError('invalid market')
    published = parse_utc(published_at)
    observed = parse_utc(observed_at)
    if published > observed:
        raise ValueError('published_at cannot be later than observed_at')
    probabilities = normalize((predictor or load_model())(headline.strip(), truncation=True, max_length=512))
    digest = hashlib.sha256((market.upper()+'\n'+published.isoformat()+'\n'+headline.strip()).encode()).hexdigest()
    return {
        'event_id': digest, 'market': market.upper(), 'published_at': published.isoformat(),
        'observed_at': observed.isoformat(), 'model': MODEL, 'probabilities': probabilities,
        'sentiment': max(probabilities, key=probabilities.get),
        'mode': 'SHADOW_ONLY', 'trade_authorized': False,
    }
