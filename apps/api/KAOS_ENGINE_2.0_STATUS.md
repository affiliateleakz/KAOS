# KAOS Trading Engine 2.0 — foundation development build

Added `kaos_risk_engine.py`: pure deterministic broker-neutral pretrade risk gate (quote freshness, finite quantities, notional, aggregate exposure, daily loss, concurrent position cap, balance, emergency stop, live authorization and consent). Verified position-closing SELL may proceed during entry risk halts, but not emergency stop. Contract quantity units fail closed until broker-specific multiplier rules exist.

Added `kaos_execution_pipeline.py`: **paper-only** risk-first dispatch with in-memory idempotency and no fabricated fills. The in-memory order cache is for development only and is not durable across restarts. The shared registry continues to block live dispatch. No automated real-money orders or new broker connectivity are claimed.

Existing Coinbase gateway remains separate and does NOT yet use this risk gate. Production integration requires persistent reservations, authenticated snapshots, broker market rules, fill and partial-fill reconciliation, and end-to-end integration tests. No live trades were placed. No production deployment was performed. Do not upload to running backend as a replacement or enable live orders.
