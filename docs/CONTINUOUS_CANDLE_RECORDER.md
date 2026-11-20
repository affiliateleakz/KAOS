# KAOS always-on candle recorder — separate supervised service

This feature closes the gap between on-demand backfill and the continuously growing archived history used by KAOS research models. **Code is added to draft PR #62 but is NOT running until deployed and supervised on an always-on worker host.** cPanel Passenger and the Chrome extension are *request-driven*, not guaranteed persistent process hosts; do not run this loop in an API worker, browser, or cPanel Python application startup hook.

## Components

- `services/collectors/continuous_candle_worker.py`: independent Python 3 stdlib poller, repeating indefinitely by default, with `--once` smoke-test mode; 60-second minimum interval. Multiple configured stocks, ETFs, crypto and forex instruments and 1m/5m/15m bars. Uses Coinbase Exchange public data for crypto, configured Alpaca IEX/SIP for stocks/ETFs, and configured OANDA v20 for FX. These are **provider-specific** prices, not Pocket Option OTC quotes. Provider credentials and market-data rights remain a separate operational prerequisite.
- `apps/api/routes_candle_recording.py`: authenticated `/api/v1/collector/candles/ingest` and `/heartbeat`. A single collector secret is required in the API server and worker host. Completed OHLCV only; source, asset, symbol, interval, UTC bar-open timestamp and deterministic identity are retained. Mongo `$setOnInsert` prevents overwriting a previously archived candle, including after worker restarts. No orders or member entitlements are modified.
- `apps/api/routes_market_backfill.py` `/prediction`: prefers this permanent same-source archived history, only falling back to the temporary on-demand history cache if archival history is not yet sufficient. Must still have an independently approved per-market AI research model. A collector alone **never** enables unapproved predictions.
- `services/collectors/market_collection_runner.py`: existing supervised news/social/filing/opportunities loop; deploy alongside the candle worker using its own provider-safe polling periods, not in the web request process.

## Configure

Copy `services/collectors/continuous_markets.example.json` to a host-managed config and adjust symbols and timeframes. The file supports 1–150 unique, validated instruments. More entries require careful provider quotas and a distributed/partitioned approach, rather than simply increasing request rate.

Set these as secrets in the worker process environment, NOT in source control or website JS:

```ini
KAOS_API_BASE=https://api.tradingwithkaos.com
KAOS_COLLECTOR_KEY=<matching-secret-on-the-API>
APCA_API_KEY_ID=<licensed-Alpaca-key>
APCA_API_SECRET_KEY=<licensed-Alpaca-secret>
KAOS_ALPACA_DATA_FEED=iex
KAOS_OANDA_DATA_TOKEN=<authorized-market-data-token>
KAOS_OANDA_ENVIRONMENT=practice
```

The API needs the same `KAOS_COLLECTOR_KEY` plus its existing Mongo connection configuration. If a provider is unconfigured, the worker records an error and continues with other configured feeds; it never substitutes fake candles.

Example supervised worker command:

```bash
python services/collectors/continuous_candle_worker.py \
  --config services/collectors/continuous_markets.example.json \
  --api https://api.tradingwithkaos.com --interval 300
```

Run a one-cycle smoke test with `--once` first. Configure systemd, Docker restart policy, or another supervisor to restart on failure and boot. A **sample systemd unit** is in `services/collectors/kaos-candles.service.example`; change absolute paths, machine user and env-file location for your worker. This PR does not remotely start the service, install the unit, or verify production credentials. Enable firewall restrictions, secret rotation, structured error collection and alerting on stale heartbeats before production.

Crypto data may be available during normal 24/7 trading, subject to provider outages. Stock and FX histories do **not** produce new bars during closed sessions. Missing bars or weekend gaps cannot simply be filled with invented prices. A market-session-aware gap validator is still required for robust stock/forex predictive models. Provider polling may miss intermediate second-level candles; this code only supports 60/300/900-second provider bars.

The worker fetches at most 300 bars per market per cycle, replays a five-candle overlap, and uses deterministic idempotent archive keys to recover from restarts. This is **limited recent-history catch-up**, not unlimited backfill. Older backfills, license enforcement, source revision handling, provider throughput, monitoring dashboards, and 5s/15s/30s resolution remain later engineering tasks. The member-facing AI score must remain experimental until archive quality and forecast calibration are independently validated.

## Verify

On the worker host, smoke test `--once` and inspect returned JSON for `markets_ok`, `markets_failed` and `bars_submitted`. Then inspect the owner-only `/api/v1/owner/candles/status` and `/api/v1/owner/candles/readiness` endpoints. In a running deployment, monitor the `continuous_candles_v1` heartbeat, symbol count and last closed timestamps; a heartbeat does not prove that the provider is still delivering fresh prices.

Run synthetic tests:

```bash
python -m unittest discover -s services/collectors -p 'test_continuous_candle_worker.py'
python -m unittest discover -s apps/api -p 'test_candle_recording.py'
```

These tests use synthetic data only. No production AI trading, option calls/puts or market accuracy is established by a passing test.
