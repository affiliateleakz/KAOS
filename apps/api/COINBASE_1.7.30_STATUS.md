# KAOS Coinbase v1.7.30 — read-only position monitoring

## Changes
- Adds a Coinbase spot position monitor for fully reconciled BUY intents with active slots.
- Reads current price through Coinbase get_product, validates product identity, rejects invalid/disabled market data.
- Uses server-side explicitly enabled per-user/product `coinbase_position_risk` settings, not browser-supplied risk values.
- Calculates fee-aware estimated net P&L and stop-loss/take-profit recommendations; stores an upserted proposal in MongoDB.
- Optional worker integration (`KAOS_COINBASE_POSITION_MONITOR=enabled`) shares the existing recovery worker lease.
- Does NOT submit SELL orders; proposals are advisory and `execution_enabled=False`.

## Validation
- 19 offline mock/unit tests pass.
- Python syntax and ZIP integrity checked.

## Not complete / do not deploy live
- Automated entry and exit execution is not implemented.
- Coinbase trading permission and SDK compatibility not verified with real account.
- No live Coinbase tests, database failover tests, or production deployment.
- Missing exchange rules/increments, available balance and fee currency handling, partial fills, client-ID lookup, stronger lease fencing and complete integration tests.
- Keep KAOS_COINBASE_LIVE_ORDERS disabled and do not replace production files.
