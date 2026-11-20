# KAOS Market Intelligence Research Dataset — phase 1

Research-only join of the existing owner candle archive and KAOS intelligence observations.

## Data source

- Candles: owner API `GET /api/v1/owner/candles/export?symbol=BTC-USD&asset_class=crypto&seconds=60&limit=5000`
- News/social: new owner API `GET /api/v1/owner/intelligence/export?asset=BTC-USD&asset_class=crypto&limit=5000`

Both owner APIs require an authenticated owner/admin and must not be exposed publicly. Do not store personal information, credentials, or raw licensed market feeds in Git.

## Build

```bash
python research/market_intelligence/build_dataset.py --candles candles.json --intelligence intelligence.json --horizons 300,3600 --output joined_dataset.json
PYTHONPATH=research/market_intelligence python -m unittest discover -s research/market_intelligence -p 'test_*.py' -v
```

The dataset joins ONLY events whose **collection time** is at or before the close of a completed candle. It computes counts of distinct news/social observation IDs in the last and previous hour and a difference. News coverage is not measured positive sentiment, nor are social observations full-platform counts. Unknown unique author counts and sentiment are explicitly null.

Existing owner candle exports are 60/300/900 seconds; **they cannot support 5-second or 30-second outcomes**, which need a separate genuine subminute archive. Price labels are indicative next-bar-open to end-of-horizon-close results. The 1h horizon requires sufficient continuous bars. Dataset rows overlap, so use purged chronological splits before fitting any model; do not feed test data into threshold selection.

## Next steps

Persist periodic structured social sample counts and unique-author counts instead of inferring them from summary strings; retain venue, sampling coverage and event timestamps. Add timestamped measured sentiment with provenance. Create source-specific collect/ingest workers, a joined dataset trainer, and walk-forward performance reports with market-appropriate fee/slippage models. None of these is implied to be deployed by this PR.
