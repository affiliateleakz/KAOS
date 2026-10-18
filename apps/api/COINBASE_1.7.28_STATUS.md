# KAOS Coinbase v1.7.28 — worker fill-reconciliation integration

Changes from v1.7.27:
- Extracted `reconcile_order(uid, client_order_id)` from the authenticated HTTP route so the recovery worker can use the same fill-ledger validation.
- Recovery worker now calls shared reconciliation after checking the Coinbase order identity; it no longer stops at status-only review.
- SELL closure requires source BUY filled quantity to equal verified SELL fill quantity; mismatches remain locked for review.
- Added three offline mocked recovery tests.

Validation: `python -m compileall -q .`; `python -m unittest -v test_coinbase_worker_mock.py` (3 passing mocked tests). No live Coinbase or MongoDB tests.

**NOT production ready.** Remaining blockers: verified signal-to-order autonomous worker; robust position management and protective exits; product rules and fee-currency accounting; partial fills; migration of old positions; consent lifecycle for workers; crash recovery for missing order IDs; Coinbase SDK and Mongo integration tests; deployment and controlled real-account validation. Live trading stays disabled. Do not overwrite production.
