# KAOS Trading 3.0 development package v0.9

**Source base:** v0.8 ZIP, not the live production deployment.

## Added
- Optional public Bluesky search sampling for configured stock cashtags; bounded search results and observed matching post/author counts, no buy/sell signals.
- Local-only short-interest position CSV reviewer to support manual short-squeeze research. **Not** an automated short-squeeze predictor or an integrated licensed feed.
- Opportunity Fusion now limits single-category repetition, exposes confirmation/conflict metadata, and marks contradictory evidence distinctly.
- Website Opportunity Radar and React Native mobile screens display agreement/disagreement and research-only limitations.
- Source-health support for `bsky-search`; documentation and offline tests.

## Preserved
- Existing website `/privacy/` route and privacy links, existing extension files, backend broker execution modules, and existing collectors.
- Unusual Whales commercial connector stays **removed**; no paid subscriptions added.

## Validation
- Collectors: 84 offline unit tests passed.
- Backend relevant: 17 offline unit tests passed.
- Python compilation and TypeScript/JSX parsing: verified during packaging.
- ZIP manifest integrity: checked during packaging.

## Limitations
- Bluesky public API accessibility, permissible commercial display, rate limits, and actual live data ingestion **not validated**.
- Manual short-interest CSV is not uploaded into member APIs; downstream distribution rights require separate review.
- Not a complete social firehose (Reddit/X/Discord not integrated), machine-learning prediction engine, real-time squeeze detector, or validated trade predictor.
- This is not a native APK/IPA, website production build, approved extension, or deployed system. Do not enable new automated trading based on these research records.
