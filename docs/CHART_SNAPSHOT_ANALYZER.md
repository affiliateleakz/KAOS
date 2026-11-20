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
