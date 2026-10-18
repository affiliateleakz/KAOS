# KAOS Trading 3.0 — market research worker (v0.3 development)

This directory is research infrastructure. **It does not trade**, cannot access broker order endpoints, and does not train a profitable AI model by itself. Existing Pocket Option and Coinbase execution code are not touched by these collectors.

## Providers and licensing

- `binance_spot.py`: public Binance spot 1-minute price candles for selected exchange symbols; may be unavailable in some regions. **Exchange spot data is NOT Pocket Option OTC pricing.**
- `dexscreener_pairs.py`: public DexScreener DEX pair liquidity and volume search; reports neutral activity, not trade signals.
- `alpaca_stocks.py`: authenticated Alpaca **stock and ETF** 1-minute historical bars. Defaults to the **IEX feed**, which represents only IEX activity, not all exchanges. SIP access depends on subscription/entitlements. A 7-day lookback is paginated completely; incomplete pagination is reported as error instead of yielding partial results.
- `tradier_options.py`: authenticated Tradier listed-options expirations + nearest-expiration chain. Defaults to sandbox (delayed) when invoked via the combined runner. A volume/open-interest ratio is **NOT directional buying**. Bid/ask spread filtering reduces poor-quality research records but does not predict profitability.

Check provider terms, licensing, data redistribution rights, quotas, and regional availability before charging users or displaying feed content commercially.

## Setup (run on your separate backend worker/VPS, not inside a mobile app)

Requires Python 3.10+; stdlib only for these four collectors.

```bash
cd collectors
export KAOS_API_BASE='https://api.tradingwithkaos.com'
export KAOS_COLLECTOR_KEY='<server-side collector secret>'
export APCA_API_KEY_ID='<alpaca market-data key>'
export APCA_API_SECRET_KEY='<alpaca market-data secret>'
export TRADIER_TOKEN='<Tradier market-data token>'

python market_collection_runner.py --config market_universe.example.json --dry-run
python market_collection_runner.py --config market_universe.example.json
```

Use `--loop --interval 300` **only** under a process supervisor on an always-on server. Don't run 24/7 collectors inside cPanel's per-request web process or the Chrome extension. A single execution is the default.

Never commit `.env` or broker keys, send secrets to the extension/mobile app, or expose the collector key to the public website. **Live-provider calls and API ingestion require real credentials and have not been validated in this offline development build.** Missing credentials are clearly reported and those providers skipped.

## Scale and coverage

The sample universe has 10 stock/ETF symbols, 3 options underlyings, 3 crypto pairs and 2 DEX searches. Edit the JSON to request up to **150 stock/ETF symbols, 100 options underlyings, 150 crypto spot symbols and 20 DEX searches per cycle**. These are code input limits, **not guarantees** of feed availability or processing throughput. Budget for provider quotas: options queries need at least two requests per underlying, stocks use paginated historical-bar requests, and repeated DEX searches consume rate limits. Do not assume every market is covered, or that a source is live.

The collector intentionally submits **summarized observations** to `/api/v1/intelligence/ingest`. It does NOT yet archive complete training-grade tick/OHLCV histories or persist option chains. Full candle archival, licensing, storage schema, backfill, point-in-time data for model training, and ETL workers are next-stage work.

## Data freshness

- Stock observations require >=21 **completed** one-minute bars and reject bars older than 30 minutes; after hours they will often produce zero observations (not an error).
- Binance samples are similarly rejected when stale; the original spot adapter is independent of Alpaca and Tradier.
- Options observations represent **chain snapshots at collection time**, not proof of trade timing, premium direction, or order-flow aggressor side. Sandbox quote data is delayed. Options selected are limited to nearest expiration and a filtered subset; counts are **not** total market-wide flow.
- The new member-only `/api/v1/intelligence/health` endpoint reports the age of stored observations by provider/asset type. `recent_observation` does not mean the source is live or that the market is open. Results may be a capped sample.

## Safety and quality checks

```bash
python -m unittest discover -v
```

The observer's `direction` is a technical description of *past* bars, never a predicted return. Options observations are **neutral**. All scores in the radar are research-priority heuristics, not winning probabilities. Production broker execution remains separate and should require explicit user approvals, independent risk rules and verified performance testing.

## Deployment migration notes

The updated `backend_foundation/routes_opportunity.py` references `kaos_source_health.py`; deploy both together and keep your existing auth/entitlement routes. If many observations are ingested, add appropriate Mongo indexes on `(source,event_id)` for idempotency and `observed_at` for the Radar/health page after checking for duplicates. This ZIP does not run any migration or alter the live database.

Original provider docs:
- https://docs.alpaca.markets/us/reference/stockbars
- https://docs.tradier.com/reference/brokerage-api-markets-get-options-expirations
- https://docs.tradier.com/reference/brokerage-api-markets-get-options-chains
