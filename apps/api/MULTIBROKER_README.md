# KAOS Multi-Broker foundation v1.7.31 (development only)

Adds a broker-neutral, typed adapter contract, broker capability catalog, normalized order intents, exchange execution reports, and validation. No new broker has been connected and no live order permissions have changed.

## Implementation sequence
1. Complete and test Coinbase FastAPI spot order and exit lifecycle, then wrap in adapter.
2. Wire existing Pocket Option browser executor through a binary-specific adapter, without sharing spot exit semantics.
3. Add OANDA (forex/CFD), Alpaca (equities/crypto), Interactive Brokers, and MT5 adapters separately.
4. Each adapter must implement authentication, symbol rules, tick/lot precision, balances, submit, lookup, fills, cancel, and recovery; broker-specific permission checks and regulatory availability must be verified.
5. Broker-neutral worker enforces server membership, consent, global emergency stop, per-user/account/symbol lease, risk limits, idempotent client IDs, fill-driven ledger, and restart reconciliation.
6. All adapters remain disabled until paper/integration tests and explicit user authorization.

Run: `python -m unittest -v test_kaos_broker_core.py`
