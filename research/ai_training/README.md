# KAOS Candle AI — offline research baseline

Research-only classifier for KAOS's owner-only candle exports. No broker orders, no trained-model deployment, no persistent model promotion.

## Run

Requires Python 3.10+, numpy and scikit-learn.

```bash
pip install numpy scikit-learn
PYTHONPATH=research/ai_training python -m unittest -v research/ai_training/test_train.py
python research/ai_training/train.py --input owner_candles.json --horizon-bars 3 --cost-bps 10 --output report.json
```

Export JSON using the authenticated owner endpoint:
`GET /api/v1/owner/candles/export?symbol=BTC-USD&seconds=60&limit=5000`.

Only complete 1m/5m/15m candles from one source/market are accepted. Missing intervals are excluded, not filled. The classifier uses lagged closed-candle features, next-open entry and future-close directional labels, and chronological 60/20/20 splits with purged label overlap. Confidence thresholds are selected on the validation slice, not the test slice.

**Limitations:** This is not connected to production inference and not evidence of a profitable strategy. Signals can overlap, costs are a configurable proxy, and no real data results are included. Run the trained classifier in paper/shadow mode and validate independent periods and realistic order costs before any possible promotion.
