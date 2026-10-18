# KAOS 1.6.51 — Multi-expiry native training API

Added `train_multi_expiry` native messaging operation. Each sample must contain `x` (104 numeric features), `label` (0/1), `t` (timestamp milliseconds), `asset`, and `targetHorizonMs` (one of 5000, 10000, 15000, 20000, 25000, 30000, 60000). The operation trains and independently validates one XGBoost model per available expiry, using the existing chronological holdout, overlap purge, and promotion gate. Rejected horizons return reports, not models.

**Limitations:** This is a trainer API, not an integrated market-data labeling pipeline or automatic model router. The current extension still calls the legacy single-horizon operation. No new pretrained profitable models or autonomous demo-trading verification are claimed. Real Pocket Option execution and profitability have not been verified.
