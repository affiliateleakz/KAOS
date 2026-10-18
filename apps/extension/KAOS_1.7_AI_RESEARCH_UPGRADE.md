# KAOS 1.7 — read-only AI research foundation

This build preserves existing KAOS live execution, UI, and historical backtester. It adds a local historical candle archive, per-agent strategy notebook, and optional read-only Pocket Option candle collector. **No broker orders, AI auto-trading, GPT/Claude/Grok model execution, or automatic profitable strategy discovery were added.** Existing research-only technical agent endpoint `/otc/analyze` remains available.

## Start the local research service

From `research_service` run `python server.py` (binds to localhost port 8765). New endpoints:

- `POST /kaos-ai/ingest`: `{ "market":"EURUSD_otc", "timeframe":5, "candles":[{"time":1790000000,"open":1.1,"high":1.2,"low":1.0,"close":1.15}] }` (sample prices only; not real PO data). Deduplicates candles by timestamp and reports gaps.
- `GET /kaos-ai/archive`: list stored market/timeframe archives.
- `POST /kaos-ai/notebook`: `{ "agent":"research", "title":"Hypothesis", "notes":"Needs out-of-sample test", "status":"untested" }`.
- `GET /kaos-ai/notebook/research`: inspect agent notebook.

Archives are stored under `research_service/kaos_research_data/` and can be converted to the existing backtest input format. No trading permissions are exposed.

## Optional upstream data collection

The GitHub repo `Rufus011/CMP-server_Pocket-option-2026` provides an unofficial async Pocket Option client. To use it, separately install the upstream Python package in a dedicated environment, supply a **demo-only** `PO_SSID` locally, then run:

`python collect_po_history.py --market EURUSD_otc --timeframes 5,15,30,60 --count 200`

Only read-only `po.candles` is called. The requested 5/15/30-second periods and depth **are not verified** against Pocket Option. Unsupported requests may fail; no trade is placed. Do not upload SSIDs, cookies, tokens or API keys. Review broker terms before using unofficial access.

## Still to validate/build

- Real broker candle fetch success, historical depth, and accurate 5s timestamp alignment.
- UI wiring for importing archive datasets and visual candle/trade replay.
- AI agent model adapters, cost controls, shared research board, automated candidate generation, and out-of-sample experiment scheduling.
- Full 20-combination evaluation; no new performance claims are made.

The upstream MIT code was **not copied** into this archive; this is an original adapter built around its documented interface.
