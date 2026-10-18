# KAOS live agent bridge — scope and setup

This build connects the existing KAOS real, closed 5-second Pocket Option candle archive to the local Python OTC research agents automatically. It uses the extension service worker and saves agent decisions to `chrome.storage.local` under `KAOS_agent_live_status_v1`. The Research Lab displays the latest result. There is no CSV import needed for the live feed.

## Run

1. Install Python 3.10+ and start `python research_service/server.py` from the extracted extension directory.
2. In Chrome extensions developer mode, load the unpacked directory containing `manifest.json`.
3. Open Pocket Option and allow KAOS to record at least 60 contiguous, real, closed 5-second candles on the chosen market. The archive saves approximately every 30 seconds.
4. Open the TradingAgents Research Lab. The Live Pocket Option agent feed shows connection and decisions. If service unavailable, start the local Python service.

## Not yet implemented / limitations

* These are the three deterministic trend, momentum, liquidity-rejection agents, **not** TradingAgents LLMs applied to OTC.
* The agent outputs are **shadow only**; they are not connected to order placement. The existing execution engine is preserved.
* This build does not establish the membership cloud, broker execution, real-time latency, or payout-adjusted profitability. A 100% working live trading bot cannot be certified without those tests.
* The bridge currently selects the most recently updated market in the archive, not all four charts.
* It requires a separately running Python service. No API subscription is required for this local analysis.
