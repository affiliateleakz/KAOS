# KAOS Coinbase v1.7.27 — atomic reservation patch

This is a DEVELOPMENT patch based on v1.7.26, not a deployment-ready autonomous bot.

Changes:
- Coinbase BUY now atomically reserves a unique MongoDB slot per user/product before attempting submission. Concurrent BUY requests cannot both reserve the same product; a definitive rejection or reconciled unfilled cancellation releases it. Ambiguous orders retain the reservation.
- Successful fully reconciled SELL releases the source BUY slot.
- The old telemetry executionAttemptId lookup is scoped to the authenticated user.
- No environment credentials are packaged.

Known limitations and risks:
- SELL full-size logic still does not handle fee-in-base, partial exits, product increments or available balances. Do not activate live orders.
- The recovery worker remains read-only and does not reconcile fills or place protective exits.
- The Coinbase API order endpoint remains manually callable; it is NOT yet wired to a verified completed-candle strategy worker.
- Atomic slots do not repair existing positions from earlier builds. Deployment requires a reconciliation/migration procedure before activation.
- MongoDB outages and ambiguous order outcomes require manual reconciliation; this is deliberately fail-closed.
- Coinbase SDK, MongoDB integration, live order, restart and end-to-end tests remain unperformed.

Keep KAOS_COINBASE_LIVE_ORDERS=disabled. Do not overwrite production without staging validation.
