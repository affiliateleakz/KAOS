# KAOS Trading 3.0 v0.4: News and SEC filings discovery (development)

## Scope and accurate interpretation

These are **research-only adapters**, not sentiment models, trade signals, or verified insider-buy alerts.

* **GDELT DOC** (`gdelt_news.py`) collects article URLs and headlines for an explicitly mapped ticker/topic query. Its `seendate` is when GDELT first observed/indexed the article; this is **not confirmed publisher publication time**. The `published_at` field is a source-time placeholder required by the common API, and every summary explicitly explains this limitation.
* **SEC EDGAR company submissions** (`sec_edgar_filings.py`) collects recent filings for *configured company CIKs*. It accepts Forms 4/4-A (ownership filing *discovery only*), 8-K, 8-K/A, 10-Q and 10-K. An observed Form 4 does not establish a buy/sell, ownership change, investment value, trade date, or politician trade. The SEC company-submissions feed may not cover every ownership filing for the issuer because reporting owners file under their own identities. SEC 13F, politician trades, and actual Form 4 transaction XML parsing are **not yet implemented**.
* The backend adds **`filing`** as a neutral event source. Opportunity Fusion treats filings/news context as *insufficient for a directional trade candidate on their own*. Directional confirmation still requires multiple sources, and trade execution remains disabled.
* URLs link to the original SEC filing or article for human verification. No news article bodies are copied or scraped.

## Configure

Edit `collectors/market_universe.example.json`:

```json
{
  "news_watchlist": [{"symbol": "AAPL", "query": "\"Apple Inc\""}],
  "sec_watchlist": [{"symbol": "AAPL", "cik": "0000320193"}]
}
```

These fields are **additional** to existing `stocks`, `etfs`, `options_underlyings`, `crypto_spot`, and `dex_queries` fields. Only add *verified* symbol-to-CIK mappings, and choose precise search queries; do not assume generic ticker text matches issuer-specific news.

Set `SEC_USER_AGENT='KAOS Research support@tradewithkaos.com'` to a monitored contact address belonging to your organization (replace this example if incorrect). SEC requests require an identifying user agent and must respect the SEC fair-access policy. Do not copy credentials into mobile/web source. GDELT requires no credential for its public DOC endpoint but can impose usage constraints; check current terms.

`python collectors/market_collection_runner.py --config collectors/market_universe.example.json --dry-run` from repo root shows up to five sample observations and per-provider errors; no ingestion occurs. For direct scripts, run from `collectors` with the same directory's config filename. Use `KAOS_API_BASE` and `KAOS_COLLECTOR_KEY` on a server-side worker to submit to your deployed API.

## Polling and operational safeguards

The combined runner defaults to minimum **15 minutes for GDELT** and **60 minutes for SEC** when `--loop` is used. Configurable via `--news-minutes` and `--sec-minutes`, with guardrails that reject shorter values. General market-data loop remains separately configured with `--interval` (>=60 seconds). The script performs synchronous HTTP requests, so actual start times may lag and workers need monitoring, retries, and durable queues for production.

**Data provenance:** SEC `acceptanceDateTime` is interpreted as US Eastern; fallback filing date has no exact time and is labeled as approximate. SEC filing dates may be later than the underlying reported transaction. GDELT first-seen timestamp does not certify when an article was written or published. Original evidence should always be reviewed.

## Deployment boundaries

Neither external provider was contacted with live credentials in this build; offline unit tests use mocked responses. No continuous worker is running, no KAOS production website or extension was deployed, and the existing order execution code is unchanged. React Native iOS/Android binary builds and website dependency builds were not run.

Related primary documentation:
- https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/
- https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data
- https://www.sec.gov/about/rss-feeds
