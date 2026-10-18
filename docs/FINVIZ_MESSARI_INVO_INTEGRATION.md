# KAOS integrations: Finviz, Messari, Invo
Reviewed 2026-10-18. This is an implementation plan. No provider credentials, commercial access or live data are claimed.

## Finviz — stock intelligence
Official: https://finviz.com/
2026-10-07 API announcement: https://finviz.com/blog/our-upgraded-api-higher-limits-clearer-data-and-more-ways-to-connect/
2026-10-09 embed maps announcement: https://finviz.com/blog/you-can-now-embed-finviz-maps-on-your-website-blog-or-app/

Integrate official map iframe through the Finviz-generated embed code, stock-screen filters, company fundamentals, unusual volume, news and insider/manager/earnings evidence. Store official API tokens server-side only. Finviz Elite's personal single-user license does not alone grant paid SaaS redistribution permission; request applicable commercial authorization before displaying API-fed results to KAOS members. No scraping or made-up endpoints. Honor limits, attribution and freshness.

## Messari — crypto intelligence
Official: https://api.messari.io/
Advertises API-key and x402 authentication with market, exchange, research, on-chain and social data. Build backend-only authenticated adapters, normalize timestamped evidence for the existing KAOS Opportunity Radar, expose provenance, handle quotas and outages. Explicit contract review for commercial display/redistribution. Do not make automatic x402 payments without separate owner approval.

## Invo — social trading, assumed https://www.invoapp.com/
Invo advertises trader profiles, track records, social content and Hyperliquid-powered crypto futures. Build trader analytics only after Invo approves authorized API/partner access and commercial usage. No public Invo developer API was verified here. Never scrape private data or auto-mimic/copy leveraged trades.

Hyperliquid provides a separate public info API: https://hyperliquid.gitbook.io/Hyperliquid-docs/for-developers/api/info-endpoint
Its public records may support an independent, correctly labeled Hyperliquid intelligence tool after terms/privacy review; do not label them Invo data.

## Rollout
1. Surface providers in a clear planned/unavailable/approved state; no fictitious data or connected statuses.
2. Add Finviz's officially generated market-map embed (review iframe CSP and allowed hosts), plus open-in-provider links.
3. Build Finviz and Messari server adapters behind disabled-by-default flags after credentials, licenses and quotas are approved. No keys in frontends.
4. Normalize observations to existing kaos_opportunity logic, deduplicate source votes and retain dates/provenance. Add mock tests for malformed/stale responses and network failures.
5. Seek Invo partner access; keep copy trading disabled pending independent execution and risk approval.
6. Gate commercial availability by entitlements, monitoring, caching rights and financial-data compliance.

Current state: none of these three external providers has been technically connected by this document. Research does not place orders.
