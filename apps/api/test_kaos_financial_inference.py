import pytest
from kaos_financial_inference import classify_headlines

def test_sentiment_predictions_from_real_classifier_interface():
    classifier=lambda texts, **kwargs: [
        {"label":"LABEL_1","score":0.9},{"label":"LABEL_2","score":0.8}]
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
