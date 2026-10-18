# KAOS Coinbase FastAPI 1.7.26 — recovery development build

Added `coinbase_recovery_worker.py`: an opt-in, standalone, **read-only** Coinbase order-status watcher using a MongoDB distributed lease. It does not submit orders, mark positions filled, or close positions. Ambiguous submissions without exchange order IDs remain blocked and flagged for manual review. The lease reduces duplicate worker activity, but the current design is not a fencing-token protocol; it is unsuitable for concurrent live order writers.

## Running in a staging environment

Use the existing Python 3.11 virtualenv and installed requirements. Set `KAOS_COINBASE_RECOVERY_WORKER=enabled` only after configuring MongoDB and encrypted broker connections. Run `python coinbase_recovery_worker.py` as a separate supervised process. No environment credentials are included in this ZIP. Do not replace the production API without staging tests and a rollback plan.

## Not finished / not live-ready

- Full exchange-fill reconciliation must be invoked and verified from the worker (currently status observation only).
- Coinbase API `client_order_id` lookup for ambiguous requests and order pagination must be verified against SDK.
- Partial fills, fee currency, min sizes, portfolio balances, SELL quantity, automatic exits and restart recovery require further implementation.
- Deterministic KAOS strategy must receive verified, **completed** Coinbase market candles; existing binary 45s expiration does not apply to spot orders.
- Worker should have fencing tokens and heartbeats; lease alone is not sufficient to authorize live execution.
- No live exchange order, deployment, or integration test has been performed.

**Keep `KAOS_COINBASE_LIVE_ORDERS=disabled`.**
