"""Optional local financial text inference worker for KAOS.

Deploy separately with explicitly installed torch/transformers and approved
model weights. Network model downloads are disabled: a local snapshot must
be provisioned by the operator. No live order or signal authority.
"""
from functools import lru_cache
from math import isfinite
import os

MODEL_ID = "trading_hero"
LABEL_SCORE = {"positive": 1.0, "neutral": 0.0, "negative": -1.0}


@lru_cache(maxsize=1)
def _classifier():
    directory = os.getenv("KAOS_TRADING_HERO_MODEL_DIR", "").strip()
    if not directory or not os.path.isdir(directory):
        raise RuntimeError("Trading-Hero model not provisioned locally")
    from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline
    # Load locally and explicitly: passing local_files_only to pipeline()
    # is version-dependent and may not reach both model and tokenizer.
    tokenizer = AutoTokenizer.from_pretrained(directory, local_files_only=True,
                                              trust_remote_code=False)
    model = AutoModelForSequenceClassification.from_pretrained(
        directory, local_files_only=True, trust_remote_code=False)
    # Never assume a generic LABEL_0/1/2 mapping means neutral/positive/negative.
    # Confirm the checkpoint's actual label configuration before scoring markets.
    raw_labels = getattr(getattr(model, "config", None), "id2label", None)
    if not isinstance(raw_labels, dict) or len(raw_labels) != 3:
        raise RuntimeError("Trading-Hero checkpoint label schema is missing")
    actual = {str(v).strip().lower() for v in raw_labels.values()}
    if actual != {"neutral", "positive", "negative"}:
        raise RuntimeError("Trading-Hero checkpoint label schema requires review")
    return pipeline("text-classification", model=model, tokenizer=tokenizer,
                    device=-1)


def classify_headlines(headlines, *, classifier=None):
    """Return scored headlines or raise; never invent model predictions."""
    if not isinstance(headlines, list) or not 1 <= len(headlines) <= 100:
        raise ValueError("Expected 1–100 headlines")
    if any(not isinstance(h, str) or not 5 <= len(h.strip()) <= 500 for h in headlines):
        raise ValueError("Invalid headline")
    predict = classifier if classifier is not None else _classifier()
    results = predict(headlines, truncation=True, max_length=256)
    if not isinstance(results, list) or len(results) != len(headlines):
        raise RuntimeError("Financial classifier returned incomplete result")
    scored = []
    for headline, result in zip(headlines, results):
        label = str(result.get("label", "")).lower()
        confidence = result.get("score")
        if label not in LABEL_SCORE or isinstance(confidence, bool) or not isinstance(
                confidence, (float, int)) or not isfinite(confidence) or not 0 <= confidence <= 1:
            raise RuntimeError("Financial classifier returned invalid prediction")
        scored.append({"headline": headline, "label": label,
                       "confidence": float(confidence),
                       "sentiment_score": LABEL_SCORE[label] * float(confidence),
                       "model_id": MODEL_ID, "execution_authority": False})
    return scored
