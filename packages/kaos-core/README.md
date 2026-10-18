# KAOS Multi-Engine Platform v0.7 — research prototype

**Not production-ready; paper simulation only. Does not connect to real brokers, train AI, handle real payments or issue trading advice.** This is the first shared source-code foundation for an all-in-one KAOS platform. It is not a completed full platform and makes no claims of profitability.

## Modules
- `kaos/core.py`: isolated crypto, stock, forex, options and Pocket Option strategy interfaces; bar validation; basic risk guard, order deduplication and fee-aware paper orders. Options and Pocket Option deliberately fail closed until contract-aware execution logic is available.
- `kaos/research.py`: OHLCV CSV research replay for crypto, stocks and forex. It is a simplistic next-open proxy, not a broker-accurate backtest. Intrabar stops are conservative, including on entry bars. OHLC data still cannot reconstruct the exact execution sequence, market spread or order queues, so this is not execution-grade validation.
- `kaos/memberships.py`: feature-gates and prototype affiliate rate calculations using *recipient's membership tier* at each referral generation, free (10/0/0), Pro (30/15/0), Ultimate (50/25/5). No payouts are made. Legal review required.
- `tests`: unit tests for entry safeguards and referral rules.

## Run (Python 3.10+; no third-party dependencies)
`python -m unittest discover -s tests -v`

`python cli.py --engine crypto --csv examples/sample.csv --symbol BTCUSD --fee-bps 10 --slippage-bps 2`

CSV required headers: `timestamp,open,high,low,close,volume`. The sample file is **synthetic**, intended to verify code wiring, not to assess performance.

## Planned integrations — not built
1. Real exchange market-data ingestion, quote/trade feeds, order book, normalizing splits, licensed options chains.
2. Broker adapters: Coinbase Advanced, Alpaca, Interactive Brokers, OANDA, existing Pocket Option adapter (subject to platform permissions).
3. Executable backtests: true tick-sequence fill handling, spread histories, limit order queues, partial fills, funding, borrow, trading calendars, corporate actions, contract multipliers/expirations.
4. Order lifecycle with idempotency across restarts, durable ledger, reconciliation, per-member account controls and kill switches.
5. Separate AI shadow-training service, scanner pipelines, website dashboard, authentication/payment integration and MLM compliance review.

**Do not use the simplistic research replay to evaluate whether a strategy is profitable.**
