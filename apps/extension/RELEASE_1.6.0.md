# KAOS Trading Bot 1.6.0 — Working Engine Restore

Current KAOS interface retained. Pocket Option market-data core restored from the known
1.1.28 LIVE_STREAM_CHART_BIND_FIX baseline.

Restored:
- po-bridge.js
- content.js
- candidate7b_strategy.js
- read-only MARKET_DATA_PROBE handshake
- visible-asset/history bootstrap
- GET_TERMINAL_SNAPSHOT chart feed

Cloud UI is not injected into Pocket Option. Manifest owns content-script injection, so
the engine is not injected twice. Legacy AlphaBot naming was removed from executable
source/UI. All JavaScript passes syntax validation.
