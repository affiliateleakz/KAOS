# KAOS FastAPI Coinbase integration — controlled development build

This patch is based on the uploaded *running* FastAPI backend, not the separate WSGI website.

## Included
- Registered FastAPI `/api/v1/coinbase-live/status`, `/orders`, `/reconcile`.
- Uses existing JWT bearer authentication, active membership, MongoDB Motor, encrypted broker vault schema.
- Server live-orders flag defaults to disabled, plus unexpired consent, emergency stop and $25 maximum order size.
- Unique order intent before Coinbase submission; ambiguous outcomes stay locked.
- SELL only against a verified KAOS BUY; reconciles actual Coinbase fills.
- Fixes simulated fallback strategy crash and disallows Coinbase trades through client-side confirmation telemetry.
- Does not bundle `.env`, backups, logs, `.pyc`, or historical ZIPs.

## Not complete / DO NOT ENABLE LIVE ORDERS
- Coinbase credential records and SDK request shapes have not been tested against your account.
- No autonomous strategy-to-order worker, restart recovery by client ID, real-time price supervision or stop-loss/take-profit automation.
- No balance, minimum increments, fee-currency or full partial-fill inventory handling.
- No exchange sandbox/integration testing or deployment verification.
- Do not enable `KAOS_COINBASE_LIVE_ORDERS` until all are implemented and validated.
- Do not upload the entire archive over a live directory. Back up the server and stage/test first.

## Important
The uploaded source archive contained `.env` and `.env.backup`. Rotate any secrets they contained.
The current strategy is a 45-second binary-option continuation signal, not a spot exit policy.
