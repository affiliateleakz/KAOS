# KAOS Political & Wall Street Disclosures Scanner

This module is distinct from Freebuff's social media scanner. It displays **documented public disclosures** rather than inferred or real-time positions.

## Supported record model
- House and Senate periodic transaction reports: reporting date, transaction date, filer, named asset, disclosed amount range, source document. Congressional transactions can be disclosed weeks after the trade.
- SEC Form 3/4/5 insider ownership filings: filing and transaction dates, grant/exercise/trade classification if verified from the actual filing.
- SEC 13F quarterly institutional portfolio disclosures: **holdings**, not buy/sell orders. Comparing two snapshots can indicate a position change but does not establish exactly when or how a trade occurred.

## Data pipeline status
The source-verified ingestion API, authenticated member search, entitlement check, and read-only UI are included here. **No scheduled live collector is connected by this PR.** The dashboard will show no records until a collector imports verified filing data. Never fabricate sample records as actual trades.

## Commercial usage gate
The House disclosure site warns against certain commercial use of its content, subject to a news/media dissemination exception; KAOS must obtain a qualified legal review before relying on an exception or ingesting House filings into a paid feature. Server variable `KAOS_HOUSE_DISCLOSURE_RIGHTS=approved` is disabled by default. Review Senate terms and each data license before commercial republishing as well.

## Collector integrity
Use HTTPS official URLs, exact filing IDs, stable deduplication, separate filing and execution dates, and per-record audit logs. Do not conflate a share grant with a market buy, or quarterly 13F holdings with today's trade. Collector requests require `KAOS_COLLECTOR_KEY`, and member reads require scanner access.

## Official starting points
- House Clerk: https://disclosures-clerk.house.gov/FinancialDisclosure
- Senate: https://efdsearch.senate.gov/search/home/
- SEC EDGAR: https://www.sec.gov/edgar/search/
- SEC official data APIs: https://www.sec.gov/search-filings/edgar-application-programming-interfaces

## Before launch
Build and test official SEC Form 4 XML and Form 13F ingestion, provenance, schedules, update/withdrawal handling, error alerts and caching that respects SEC rate limits and declared User-Agent. Complete House/Senate licensing review; independently certify sources. No auto-trading or purported insider knowledge.
