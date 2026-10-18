# KAOS Trading Bot 1.6.3

Deep data-wiring repair:
- Pocket Option terminal snapshot now exposes up to 500 completed trade records.
- Dashboard stats, Trade History, and Performance all consume the same live trade source.
- Dashboard stats are larger/readable.
- Trade History is populated from the live engine instead of stale popup-local storage.
- Four-chart Performance uses full live trade history rather than only the last 40 trades per chart.
- AI outputs with no valid trained samples show COLLECTING instead of a misleading 0.00%.
- Cloud startup treats bot-config/release endpoints as optional. A valid authenticated membership/device session is no longer marked OFFLINE merely because an optional endpoint fails.
- Offline cloud screen includes CONTINUE WITH LOCAL BOT, so cloud never blocks Pocket Option/local trading UI.

Trading strategy and Pocket Option live-stream execution logic are unchanged.
