# KAOS Trading 3.0 v0.6 — public institutional and social evidence

**Development-only source; not live deployed; research only. No broker order execution.**

## New modules

- `sec_13f_holdings.py` — watches up to 20 explicitly configured US institutional filer CIKs; discovers *recent* SEC Form 13F-HR filings and parses the associated 13F information-table XML. Takes up to 25 largest **as-filed** holdings per filer, labeled with exact CUSIP (without guessing ticker), issuer, security class, reported value, shares, manager, quarter-end report date, and SEC submission date. Every observation is neutral. The filing is a **delayed quarter-end holdings snapshot**, never evidence of a current purchase/sale or full live institutional flow. Amendments not yet reconciled. Filing document download can fail with SEC blocking or changing file format; errors are surfaced, never replaced with invented results. SEC reports use as-filed units; no dollars inferred from the value without confirming the filing's unit convention.
- `bluesky_social.py` — samples up to 30 **explicitly configured public Bluesky author feeds**, searching only up to the latest 100 items per author for $CASHTAG matches. A single neutral per-hour observation reports distinct matching post count and author count over a rolling 60-minute window (excluding reposts), linked to a public example. This is **not comprehensive social scanning, a Reddit/WallStreetBets feed, a bot detector, verified sentiment, platform-wide mention count, or social acceleration**. The public read endpoint may reject requests or have quotas; such outcomes are surfaced as provider errors. No private messages accessed or full post text stored in KAOS observation.
- `market_collection_runner.py`: optional `institutional_managers`, `social_accounts`, `social_cashtags`; 13F minimum polling 360 minutes; social 15 minutes. Default sample config leaves manager and account lists empty (opt in).
- `backend_foundation/kaos_source_health.py`: tags `sec13f` and `bsky-social` events.
- Website and mobile Opportunity Radar: filters for institutional 13F and social evidence, with source-quality caveats. No changes to extension's live-trading authority.

## Example configuration

Update `collectors/market_universe.example.json` after identifying **correct manager CIKs** and public account handles; do not treat hypothetical examples as validated accounts:

```json
{
  "institutional_managers": [{"name": "SEC-listed manager name", "cik": "0000000000"}],
  "social_accounts": ["public-handle.bsky.social"],
  "social_cashtags": ["GME", "AMC", "AAPL", "NVDA", "TSLA"]
}
```

Use the valid CIK and handle you actually want to monitor, not the placeholders. `SEC_USER_AGENT` must be an actual organization+contact email permitted by SEC fair-access rules. API credentials and KAOS collector authentication are **server-side**, never mobile or site bundles.

```bash
cd collectors
export SEC_USER_AGENT='Your Organization real-monitored-contact@example.org'
python market_collection_runner.py --config market_universe.example.json --dry-run
# Only when deployed to your server with verified KAOS_API_BASE and KAOS_COLLECTOR_KEY:
python market_collection_runner.py --config market_universe.example.json
```

A dry run may query configured public providers, but does not submit observations to KAOS or place trades. If neither managers nor public accounts are configured, these two new adapters are idle. Request pacing and commercial redistribution policies must be assessed before running this continuously for paid members. A production worker needs scheduling, persistent logs, source-health alerts, observability, and retry/backoff.

## Validation

Offline Python collector tests, backend opportunity and health tests, TS/JS source parsing, Python compile and ZIP integrity were run. No live SEC/Bluesky network data was collected during these tests and nothing was deployed. Production Expo builds and full website builds have not been run. No guarantee of 100+ live streams or of predictive performance.

## Source docs

- SEC EDGAR APIs: https://www.sec.gov/edgar/sec-api-documentation
- SEC 13F data sets: https://www.sec.gov/data-research/sec-markets-data/form-13f-data-sets
- Bluesky public app API: https://docs.bsky.app/docs/api/app-bsky-feed-get-author-feed
- Bluesky API auth/routing: https://bsky.network/docs/api-directory/

No Unusual Whales connector is included.
