# Milestones (each one is a small PR with an acceptance test; stop and ask at every gate marked ⛔)

| # | Milestone | Acceptance test | Stop condition |
|---|---|---|---|
| M0 | Baseline repo, audit docs, `make dev`, CI | CI green. Site loads at :3000. `/api/health` returns ok. Demo login works | — |
| M1 | Membership tiers + receiver-based 3-level affiliate ledger (preview only) | Fixtures: Free/Pro/Ultimate, mixed tiers, renewals, refunds/chargebacks, cycles, idempotency | ⛔ No real payouts |
| M2 | Paper order lifecycle demo (API + portal) with risk limits and kill switch. *API part done. Remaining: authorized quote feed, fills/P&L, portal UI* | Integration test: place → fill → reconcile → audit log, all paper | ⛔ No live broker orders |
| M3 | Extension: load v1.7.x locally against the local API. Resolve key/ID | Extension logs in, syncs a paper trade | ⛔ Before any Web Store upload |
| M4 | Branding + pricing reconciliation | Founder sign-off on screenshots | Needs founder decision |
| M5 | Historical data schema + backtest harness on authorized BTC-USD / SPY | Reproducible backtest with costs and walk-forward split | Results reported honestly |
| M6 | Mobile app MVP against local API | Expo run, login, dashboard | ⛔ Before store submission |
| M7 | Staging deploy + secrets rotation | Staging smoke tests | ⛔ Before production |
