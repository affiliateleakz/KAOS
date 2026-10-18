# KAOS Coinbase v1.7.29 — reconciliation bug fix + read-only position policy

## Changes
- Fixes a NameError in `routes_coinbase.reconcile_order` (`req.client_order_id` outside HTTP handler); worker now receives reconciliation result.
- Validates exchange-reported `filled_size` against the persisted fill ledger when provided. A mismatch fails closed.
- Rejects truncated persisted ledgers above the configured 10,000-fill safety cap.
- Preserves meaningful HTTP status for explicit manual-review conditions instead of converting all to 502.
- Adds deterministic read-only position exit policy using estimated quote-currency fees and net P&L; supports STOP_LOSS, TAKE_PROFIT, KAOS_STRATEGY_SELL, HOLD. Does NOT place orders.
- Adds offline regression tests.

## Validation
`python -m unittest -v test_coinbase_worker_mock test_coinbase_reconcile_mock test_coinbase_position_policy`: 13 passing offline tests.
`python -m compileall -q .`: pass.
ZIP CRC check: pass.

## Still blocking real-money autonomous operation
- Live strategy-to-order worker and broker-specific spot market-data feed.
- Actual SELL submission from protective exit policy, with explicit authorization and per-position risk settings.
- Product increments, minimums, account balance, fees in non-quote currencies, and partial fills.
- Exchange order lookup by client ID for ambiguous submissions; migration/reconciliation of legacy positions.
- Worker lease fencing and lifecycle testing against MongoDB Atlas under concurrency/failover.
- Coinbase SDK version compatibility, real credential permission checks, staging and controlled real-account validation.
- End-to-end tests and safe deployment process.

This is a development build. Do not overwrite production or enable live trading.
