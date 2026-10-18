# KAOS Coinbase live activation — operator gate

Founder requested eventual live trading on 2026-10-18. This instruction
is NOT sufficient evidence of a safe authenticated broker connection and
does not activate the environment toggle.

## Existing execution mechanism
- Existing source: apps/api/routes_coinbase.py
- Server env flag KAOS_COINBASE_LIVE_ORDERS remains disabled unless explicitly set to enabled in an approved runtime.
- Requires time-limited member live-trading consent, connected credentials, order-size controls and emergency stop.
- Coinbase order status and balance need authoritative broker reconciliation. A successful test suite does not prove end-to-end execution.

## Before production activation
1. Identify the exact Coinbase account, auth scopes and trading-enabled products, and verify with the account owner.
2. Verify production API hostname, product increments, fee model, funds, membership and account isolation.
3. Run sandbox/simulated failure matrix: duplicate POST, gateway timeout after broker acceptance, partial fills, restart, missing-from-first-page order, revoked key, position close, emergency stop.
4. Independently verify that uncertain order state cannot release a duplicate BUY or unlock a risk slot. Confirm exits remain available under emergency stop.
5. Obtain explicit owner confirmation of broker/account, maximum order USD, allowed products, risk limits and rollout.
6. Enable only in verified deployment with explicit consent; execute an authorized small initial order and inspect broker order/fill/ledger.
7. Maintain rollback switch and operational monitor. Switch off immediately upon unreconciled order, stale quote, broker outage or missing risk data.

No secret or API-key value belongs in GitHub. Flag is not enabled by this file.

## Branch and release procedure
- PRs #1–#7 were merged to main on 2026-10-18.
- PR #8 has merge conflicts after retargeting to main. Its colors/branding must be reconciled while preserving privacy changes.
- PRs #9–#12 depend on later branches; do not force them into main without reconciling #8 and combined test verification.
- Deployment requires separate host/environment action; merging is not deployment.
