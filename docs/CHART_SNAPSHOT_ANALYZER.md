# KAOS Chart Snapshot Analyzer (research only)

- Accessible from authenticated member KAOS AI dashboard for users with `aiInsights` entitlement.
- Paste or upload PNG/JPEG/WebP chart screenshots (under 1.5 MB), preview locally.
- `POST /api/v1/ai/chart-snapshot/analyze` sends the image to configured OpenAI vision model, for qualitative trend, candidate formations, support/resistance, bull/bear scenarios. **No price targets, guaranteed trade signals, calibrated confidence or automated orders.**
- `GET /api/v1/ai/chart-snapshot/similar` searches the existing MongoDB `kaos_research_candles` archive for nearest 20-bar closing-price structures and next-five-bar proxy returns; nonoverlap among returned examples. This comparison **does not extract OHLCV from the screenshot**. The asset/timeframe is separately entered by the member. Empty archive -> unavailable instead of fabricated results.
- Source data must have contiguous candles with one price source; no cross-source synthetic merges.
- Screenshot is not saved in KAOS. When analyzed, it is sent to OpenAI. Disclose that to users and ensure privacy/consent requirements are met before deployment.
- Require `OPENAI_API_KEY` on backend for image interpretation. Optional `KAOS_CHART_VISION_MODEL` (defaults to `gpt-4.1-mini`). Provider call may incur API charges and rate limits.
- The current entitlements restrict the analyzer to plans with `aiInsights`. No automatic deployment.
- Based on the general product concept of historical pattern matching; original implementation, not a copy of iC Candle source.

## Known limitations

The visual description does **not** predict verified future returns. Historical analog selection is descriptive and subject to selection bias; five nearest matches are not enough to claim an actual win probability. No similarity model has been tested out-of-sample. Timezones and future outcomes use archive bar timestamps; price returns do not simulate spread, slippage, short funding, position sizing or payout. Real-world screenshots may hide enough information that meaningful analysis is impossible.

Run `PYTHONPATH=apps/api python -m unittest apps/api/test_chart_similarity.py` to check the matcher.

## Admin OpenAI configuration and combined research view

Admin → API Keys & Integrations already supports encrypted OpenAI credentials. This PR updates its OpenAI entry to list **Chart Screenshot Analyzer (vision)** and to expose an optional `KAOS_CHART_VISION_MODEL` setting (default `gpt-4.1-mini`). The provider connection check tests API-key access, **not** whether a particular vision model is available on the account. No secret is written to Git.

The KAOS AI member page now offers **Analyze chart + compare history**. That action calls the vision interpreter and archived-candle similarity service for the same user-entered market/timeframe, displaying each result independently, including a useful partial result if one service is unavailable. The historical matching remains **independent of the screenshot content**; it is not a validated screenshot-to-price prediction. This is a foundation for later verified screenshot pattern extraction and historical outcome matching.

## Structured screenshot pattern linking — experimental

The vision response now uses a restricted structured JSON schema: `pattern` is one of `uptrend`, `downtrend`, `range`, `breakout_up`, `breakout_down`, or `unknown`; explanatory text and opposing scenarios are returned separately. The combined action only requests historical *pattern category* matches if the vision response is not `unknown`.

The archive matcher calculates the same coarse category on fully closed OHLCV windows and filters candidates to that category. **Within that category, candidates are still ranked by similarity to the latest archived candle sequence, not similarity to the screenshot's pixel geometry.** No calibrated probability, identified formation verification, or price prediction is inferred from matching the category. For unknown screenshot patterns, the automatic matching step is skipped and the user can run the independent archive search. This prevents invented visual-to-numeric similarity.

The category classifier is a deterministic, intentionally simple prototype and must be evaluated and refined using authentic candle archives, with held-out historical validation and a no-trade outcome for uncertainty, before marketing it as a predictor.

## ChartScanAI research assessment — potential visual detector

The MIT-licensed [Omar-Karimov/ChartScanAI](https://github.com/Omar-Karimov/ChartScanAI) is a YOLOv8/Ultralytics-based Streamlit prototype that visualizes detection boxes and detects buy/sell classes from chart screenshots. It also generates standardized charts using yfinance/mplfinance. This is an architecture reference only: bounding-box detection confidence **does not** establish calibrated market-direction accuracy, and the repo does not demonstrate transferable KAOS trading profitability.

The repo includes a pretrained `custom_yolov8.pt` of approximately 52 MB. Do not import that checkpoint or YOLO package into production KAOS without reviewing provenance, data licensing, model weights rights, independent validation and *Ultralytics licensing* (upstream framework terms may differ from the repository's MIT license).

KAOS now contains `apps/api/kaos_chart_detection.py`, an **original, standalone, dependency-free detector result adapter** for a future licensed model. It validates labels, score, image dimensions and bounding boxes; converts pixel boxes to normalized image coordinates; applies a confidence threshold; and explicitly calls the output a detector score rather than a trade probability. Synthetic unit tests verify these boundary conditions.

**Not yet implemented:** model installation, automatic YOLO execution, bounding box inference, annotated screenshot output, or a validated labeled chart dataset. The adapter is not wired to a public prediction endpoint, deliberately avoiding an illusion of a working detector. Next would be (1) dataset governance, (2) independently licensed model choice, (3) offline annotation and validation, (4) opt-in optional worker, (5) frontend overlays with truthful labels. Production-facing screenshot interpretation continues using the existing OpenAI vision endpoint.
