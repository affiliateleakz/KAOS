# KAOS Trading 3.0 v0.6 — SEC 13F + social monitoring (development only)

Built from `KAOS_3_0_WHALES_INSIDERS_FREE_SOURCES_V0_5_1_DEV.zip`.

## Changes
- New `collectors/sec_13f_holdings.py`: neutral SEC 13F-HR recent-filing quarterly holdings snapshots by configured manager CIK, with exact CUSIP, filing and report dates.
- New `collectors/bluesky_social.py`: public author-feed cashtag monitoring, limited to configured accounts and ticker lists; neutral contextual evidence.
- Both integrated into multi-provider `market_collection_runner.py`; sample configs optional / disabled by default, no new paid credentials.
- Added source-health identifiers to backend, filter buttons and caveats to website and React Native mobile dashboard.
- Added offline fixtures/tests. No change to trading engine, execution routes, broker adapters or extension trading logic.

## Checks
- 53 collectors tests + 7 backend tests passed.
- Python source compiled; TSX and JSX parsed with TypeScript compiler.
- ZIP integrity checked.

## Incomplete / not implied by this package
- No production API keys, live validation, deployments, membership or brokerage integration testing, app binaries or real AI training.
- No general all-Reddit social scanner, all-manager 13F universe, politician disclosures, historical ownership diffs, options tape, dark pool feed or trading signals.
- All new source observations are explicitly **neutral context**; no win-rate claims.
- SEC and Bluesky terms, rate limits, commercial usage and attribution should be verified before launching a paid redistribution product.
- Unusual Whales integration remains removed.
