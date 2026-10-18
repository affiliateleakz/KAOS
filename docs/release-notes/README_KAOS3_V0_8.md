# KAOS Trading 3.0 v0.8 — incremental options activity + congressional review

**Development-only package. Not deployed. Research-only; no change to live broker execution.**

## Implemented

1. `collectors/options_activity.py` — opt-in Tradier options chain volume-change monitoring. Compares the same contract across two snapshots **from the same UTC date, expiration and environment**, with at least one minute and at most 60 minutes elapsed. Checks quote validity, bid/ask spread, minimum volume increase (100), and change-to-reported-OI ratio (>=0.75) before emitting **neutral** options activity observations. Increases in *cumulative* option volume are **not a tick/print tape, buyer/seller initiation, block trade, institutional identification, or reliable directional signals**. Uses Tradier market-data endpoints only, never order routes.
2. `collectors/market_collection_runner.py` — optional `options_activity_underlyings` setting, default `[]`. Option snapshots are persisted in `KAOS_OPTIONS_ACTIVITY_STATE` (or `./options_activity_state.json`) only after successful delivery to the authenticated KAOS intelligence API; dry runs do not advance stored state. No observations on first snapshot is normal. Configure worker on a persistent VPS with Tradier credentials and membership-authorized KAOS backend.
3. `collectors/congressional_disclosure_review.py` — **local CSV review only** for manually checked House/Senate transaction disclosures; preserves transaction-versus-filing dates, original official links, report IDs, original amount-range text and uncertain tickers. No scraping, no KAOS backend submission, no redistribution, and no automatic trade classification; this is intentional pending legal/commercial-use review.
4. Website Opportunity Radar and Android/iPhone research interfaces updated with options activity, congressional review notices and filter labels; the latest v0.7.1 website privacy-page/link updates preserved. Existing extension and broker execution unchanged.

## Enable the options activity monitor

Edit `collectors/market_universe.example.json`:

```json
"options_activity_underlyings": ["SPY", "AAPL"]
```

Supply `TRADIER_TOKEN`, `KAOS_API_BASE` (HTTPS), and `KAOS_COLLECTOR_KEY` as backend-worker environment variables. `tradier_sandbox:true` uses **delayed/sandbox data**; verify market-data entitlements and commercial redistribution rights before enabling on a paid KAOS service.

```bash
cd collectors
python market_collection_runner.py --config market_universe.example.json --dry-run
# With verified credentials, endpoint and provider terms on your controlled worker:
python market_collection_runner.py --config market_universe.example.json --loop --interval 300
```

A dry run may issue network calls to enabled providers but never commits snapshot state or transmits results to KAOS. First successful ingested cycle establishes the baseline; later cycles can detect changes. Snapshots are observational and will have no observations when conditions are unmet. If the KAOS ingest endpoint fails, its source state does not advance.

## Review congressional disclosures offline

The official [House Financial Disclosure](https://disclosures-clerk.house.gov/FinancialDisclosure) website notes that disclosures are public; the [House search page](https://disclosures-clerk.house.gov/FinancialDisclosure/ViewSearch) also states legal restrictions on commercial use. Do **not** connect this into a paid member feed or redistribute copies without legal review. Senate disclosures have separate access terms.

```bash
cd collectors
python congressional_disclosure_review.py congressional_disclosure_template.csv --output private_disclosure_review.json
```

Input CSV is deliberately empty except for column headings. No politician holdings, trades, or amount ranges were fabricated for demonstration.

## Verification and limitations

- 69 focused offline collector unit tests passed; code compilation checked.
- Existing broker/extension code was copied unchanged; website privacy route remains `/privacy/` but it still requires publication to the live domain.
- Live Tradier API, backend delivery, SEC sites, Chrome extension, production website, Android APK, and iPhone build **not verified** in this release.
- Unusual Whales remains excluded. No premium market data subscription automatically added.
- No automated trading decisions, promised win rate, or future-looking data substituted.

Official documentation: https://docs.tradier.com/reference/brokerage-api-markets-get-options-chains
