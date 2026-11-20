"""Assemble chart and catalyst features for offline research."""
from catalyst_learning_rows import make_catalyst_example
from chart_pattern_features import features_at

def make_market_example(entry, exit_quote, horizon, observations=(), candles=(), periods=(5,15,30,60,300,900)):
    row = make_catalyst_example(entry, exit_quote, horizon, observations)
    row["chart_features"] = features_at(candles, entry["observed_at"], symbol=entry["symbol"], source=entry["source"], periods=periods)
    return row
