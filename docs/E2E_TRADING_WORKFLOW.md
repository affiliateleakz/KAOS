# End-to-end KAOS trading workflow: status

Founder priority (PR #6 comment 6253698228): a working path from login to the paper portfolio, using real market data, with each step shown working and the missing steps listed honestly. **Paper only.** AI-controlled execution and real-money trading stay locked.

| # | Step | Status | Where / evidence |
|---|------|--------|------------------|
| 1 | Member login | Works (local) | Cookie JWT auth, `apps/api/auth.py`; browser login test on PR #1 |
| 2 | Choose broker | Works (paper) | Per-broker license, `compute_license(..., broker)` (#4). The Pocket Option referral rule applies only to Pocket Option. Paper Trading tab broker picker (`GET /api/v1/paper/brokers`): KAOS Paper (Coinbase market data) is available; Pocket Option and Coinbase live are listed as unavailable, each with its reason. |
| 3 | Authorized market-data feed | **Works for crypto spot** | `apps/api/market_data.py`: Coinbase Exchange **public** ticker (`api.exchange.coinbase.com/products/{id}/ticker`), free, no account or key. `GET /api/v1/paper/quote/{symbol}`. **Stocks, options and forex: no licensed feed yet (returns 503).** Pocket Option has no public data API. |
| 4 | Charts: Free 1, Pro/Ultimate max 4 | Partial | Portal: one live candlestick chart (`GET /api/v1/paper/candles/{symbol}`, closed bars, EMA20/50, fill markers). Extension 1–4 selector limited by the server `chartLimit`; server `chartSlot` checks (403 `chart_limit`). Web portal and mobile have no multi-chart view. Four concurrent charts not performance-tested. |
| 5 | Unlimited watchlists, separate from active charts | Not built | No watchlist model yet. Will not count against `chartLimit`. |
| 6 | Strategy-mode signal with documented reason | Works (paper, crypto) | `POST /api/v1/paper/signals/{symbol}` runs KAOS Structure v2 (`kaos_structure_v2.py`, vendored unchanged; v2.1 audit FAIL, labelled unvalidated) on the last closed candle and stores the action, setup, reasons, indicators and quote in `paper_signals`. On live data it is mostly HOLD. |
| 7 | Paper order | Works | `POST /api/v1/paper/orders`, omitting `quote_price` |
| 8 | Simulated fill from a timestamped quote | **Works (crypto)** | BUY fills at the ask, SELL at the bid. The quote is fetched server-side at order time. The full quote (bid/ask/last, `quote_time`, `fetched_at`, `source`) is stored on the order as `execution_kind: market_data_paper`. Manually priced orders are labelled `manual_demo`. |
| 9 | Risk manager approves or rejects | Works | The signal carries a risk decision from the same `check_order` call the order path uses; `POST /signals/{id}/execute` only fills approved, unexpired (120 s) signals, once per signal. | `kaos_risk_engine`: quote older than 10 s is refused; notional, exposure and position limits; kill switch; long-only. |
| 10 | Portfolio / fees / trade journal | Works | Cash, positions, average cost, realized P&L, simulated fee (`KAOS_PAPER_FEE_RATE`, default 0.6% per side, an assumption); durable SQLite journal plus Mongo `paper_orders`/`paper_order_rejections`. |
| 11 | Persistence / reconnection | Works | The session (broker, market, candle size, size) is stored in `paper_sessions`; the book is rebuilt from stored orders; the signal journal persists; retries are idempotent. No live-streaming reconnect yet (quotes are polled every 5 s in the portal). |

## Known limits
- The ticker's `time` is the last trade time, so thin products whose last trade is over 10 s old are refused as stale. That is by design.
- One paper book holds both manual-demo and market-data fills. Each order is labelled, but P&L is not yet split by kind.
- Coinbase public market data is used under Coinbase's API terms for display and simulation only. Check the terms before any commercial redistribution.

## Tests
`apps/api/test_market_data_paper.py`: ticker parsing, ask/bid fills with provenance, stale-quote refusal, kill switch, idempotent retry without a second fetch, conflict 409, manual-demo label, book rebuild, and a 503 for asset classes without a feed.

## One session across clients

All three clients read and write the same server-side paper account (`/api/v1/paper/*`, same user via cookie or bearer token):

| Client | Where | Status |
|---|---|---|
| Website / member portal | Dashboard → Paper Trading (`PaperSession.jsx`) | Works: broker picker, live chart, strategy signal, risk decision, execute, fees, journal. |
| Chrome extension | Bot terminal → PAPER SESSION tab (`kaos-paper-panel.js`, proxied by `background.js` `KAOS_PAPER` with a path allowlist) | Built: quote, book, fees, signal + risk, execute, journal. The bearer-token API path is verified with curl against the local stack; the panel has not been clicked through in a loaded extension yet. |
| Mobile (Expo, Android/iPhone) | ★ Paper → `app/paper.tsx` | Built and type-checks (`tsc --noEmit`): live candle chart, quote, book, signal + risk, execute, journal. Not run on a device or simulator yet. |

The extension's Pocket Option strategy bot is **not** connected to this paper session: Pocket Option has no authorized market-data API, so its trades cannot be priced from a server-side feed.
