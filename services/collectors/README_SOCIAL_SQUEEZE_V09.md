# KAOS Trading 3.0 v0.9 — social discovery and squeeze research

## Free public Bluesky search sampling
- `bluesky_search.py` queries the public Bluesky `searchPosts` endpoint for up to 20 exact cashtags; without a valid public AppView response, it records a provider issue and generates no fake observations.
- Add `social_search_cashtags` to `market_universe.example.json`. Example: `GME`, `AMC`, `NVDA`.
- The existing `market_collection_runner.py` invokes public search only on its social polling schedule (default at least every 15 minutes). No account credentials are stored in mobile/web JS.
- Results are **neutral context** and at most 100 returned posts per symbol. The 60-minute and preceding-60-minute figures are limited to that bounded result set, not platform-wide volume, momentum, sentiment or verified bot filtering. Data licensing and commercial display requirements must be reviewed before production use.
- AppView availability can differ by region, authentication or rate limits; errors surface in the runner issues list.

## Local-only short-interest position research
- Use authorized, correctly dated short-interest **position** data, not daily short-sale volume.
- Copy `short_interest_template.csv` to your own file and fill in the seven required columns from sources you have permission to use. Both `as_of` and `published_at` dates are required.
- Run: `python short_interest_review.py my_authorized_short_positions.csv`.
- The local output calculates `short_float_percent` and `days_to_cover`, and a simple **research-watch screen** when 15% of float and 3 days to cover are both met from a record published within 21 days and measured within 35 days. A reported percentage above 100% is retained with a warning because published short interest can exceed estimated float. These are transparent, non-validated research heuristics, not an estimated probability or a trading signal.
- No dataset, broker or access key is bundled; nothing is uploaded to the paid KAOS member feed. The actual figures depend on your source and might lag.
- FINRA explains that daily short-sale volume is not the same as reported short interest: https://www.finra.org/investors/insights/short-interest

## Research ranking safeguards
- At most one highest-weight vote per (source category, direction); repeated posts/articles from one source category cannot falsely become independent confirmations.
- Mixed/opposing directional evidence is labeled `conflicting_evidence`; two **agreeing independent source categories** are necessary for `research_candidate`.
- Neutral sources add context but cannot confirm a direction. A source category is not guaranteed to represent an independent market participant.
- Research scores are deliberately not win-rate estimates, probabilities, recommendations or trading instructions.
- Existing trading execution components are unchanged; this module does not place orders.

## Before deploying
- Back up and diff against your current live website and extension versions. Do not assume this ZIP matches deployed source revisions.
- `https://tradingwithkaos.com/privacy/` must resolve to the actual policy without sign-in for Chrome Web Store review. The website route and footer links remain in source; this package does NOT deploy the site.
- No live provider, production backend, Chrome extension or native phone testing is represented by offline unit tests.
