import pytest
from kaos_financial_inference import classify_headlines

def test_sentiment_predictions_from_real_classifier_interface():
    classifier=lambda texts, **kwargs: [
        {"label":"positive","score":0.9},{"label":"negative","score":0.8}]
    rows=classify_headlines(["Strong earnings outlook","Unexpected earnings miss"],classifier=classifier)
    assert [x["sentiment_score"] for x in rows] == [0.9,-0.8]
    assert all(x["execution_authority"] is False for x in rows)

def test_failed_classifier_is_not_replaced_with_guess():
    def failed(*args,**kwargs): raise RuntimeError("model offline")
    with pytest.raises(RuntimeError,match="model offline"):
        classify_headlines(["Stock earnings headline"],classifier=failed)

def test_unknown_label_fails_closed():
    with pytest.raises(RuntimeError,match="invalid prediction"):
        classify_headlines(["Stock earnings headline"],
                           classifier=lambda *a,**k:[{"label":"BUY","score":0.99}])

def test_incomplete_output_fails_closed():
    with pytest.raises(RuntimeError,match="incomplete"):
        classify_headlines(["Stock earnings headline"],classifier=lambda *a,**k:[])


def test_offline_loader_disables_remote_code(monkeypatch, tmp_path):
    import sys
    from types import SimpleNamespace
    import kaos_financial_inference as inference
    calls = []
    class Loader:
        @classmethod
        def from_pretrained(cls, directory, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(config=SimpleNamespace(
                id2label={0: "neutral", 1: "positive", 2: "negative"}))
    fake = SimpleNamespace(AutoTokenizer=Loader,
        AutoModelForSequenceClassification=Loader,
        pipeline=lambda task, **kwargs: lambda texts, **kw: [
            {"label": "positive", "score": 0.9} for _ in texts])
    monkeypatch.setitem(sys.modules, "transformers", fake)
    monkeypatch.setenv("KAOS_TRADING_HERO_MODEL_DIR", str(tmp_path))
    inference._classifier.cache_clear()
    try:
        assert callable(inference._classifier())
        assert inference.classify_headlines(["Market profits rise"])[0]["label"] == "positive"
        assert len(calls) == 2
        assert all(c["local_files_only"] is True and
                   c["trust_remote_code"] is False for c in calls)
    finally:
        inference._classifier.cache_clear()


def test_model_loader_rejects_unknown_label_order(monkeypatch, tmp_path):
    import sys
    from types import SimpleNamespace
    import kaos_financial_inference as inference
    class Loader:
        @classmethod
        def from_pretrained(cls, directory, **kwargs):
            return SimpleNamespace(config=SimpleNamespace(
                id2label={0: "SELL", 1: "BUY", 2: "HOLD"}))
    fake = SimpleNamespace(AutoTokenizer=Loader,
        AutoModelForSequenceClassification=Loader,
        pipeline=lambda *a, **k: "loaded")
    monkeypatch.setitem(sys.modules, "transformers", fake)
    monkeypatch.setenv("KAOS_TRADING_HERO_MODEL_DIR", str(tmp_path))
    inference._classifier.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="label schema"):
            inference._classifier()
    finally:
        inference._classifier.cache_clear()


def test_generic_positional_labels_are_not_treated_as_sentiment():
    with pytest.raises(RuntimeError, match="invalid prediction"):
        classify_headlines(["Unexpected earnings miss"],
                           classifier=lambda *a, **k: [{"label": "LABEL_2", "score": 0.99}])


def test_checkpoint_mapping_resolves_generic_output_labels(monkeypatch, tmp_path):
    import sys
    from types import SimpleNamespace
    import kaos_financial_inference as inference
    class Loader:
        @classmethod
        def from_pretrained(cls, directory, **kwargs):
            return SimpleNamespace(config=SimpleNamespace(
                id2label={0: "neutral", 1: "positive", 2: "negative"}))
    fake = SimpleNamespace(
        AutoTokenizer=Loader, AutoModelForSequenceClassification=Loader,
        pipeline=lambda task, **kwargs: lambda texts, **kw: [
            {"label": "LABEL_2", "score": 0.91}])
    monkeypatch.setitem(sys.modules, "transformers", fake)
    monkeypatch.setenv("KAOS_TRADING_HERO_MODEL_DIR", str(tmp_path))
    inference._classifier.cache_clear()
    try:
        result = inference.classify_headlines(["Earnings decline sharply"])
        assert result[0]["label"] == "negative"
        assert result[0]["sentiment_score"] == -0.91
    finally:
        inference._classifier.cache_clear()


def test_string_keyed_checkpoint_id2label_is_resolved(monkeypatch, tmp_path):
    import sys
    from types import SimpleNamespace
    import kaos_financial_inference as inference

    class Loader:
        @classmethod
        def from_pretrained(cls, directory, **kwargs):
            return SimpleNamespace(config=SimpleNamespace(
                id2label={"0": "neutral", "1": "positive", "2": "negative"}))

    fake = SimpleNamespace(
        AutoTokenizer=Loader, AutoModelForSequenceClassification=Loader,
        pipeline=lambda *a, **k: lambda texts, **kw: [
            {"label": "LABEL_2", "score": 0.93} for _ in texts])
    monkeypatch.setitem(sys.modules, "transformers", fake)
    monkeypatch.setenv("KAOS_TRADING_HERO_MODEL_DIR", str(tmp_path))
    inference._classifier.cache_clear()
    try:
        result = inference.classify_headlines(["Earnings miss expectations"])
        assert result[0]["sentiment_score"] == -0.93
    finally:
        inference._classifier.cache_clear()
