# End-to-end KAOS trading workflow: status

Founder priority (PR #6 comment 6253698228): a working path from login to the paper portfolio, using real market data, with each step shown working and the missing steps listed honestly. **Paper only.** AI-controlled execution and real-money trading stay locked.

| # | Step | Status | Where / evidence |
|---|------|--------|------------------|
| 1 | Member login | Works (local) | Cookie JWT auth, `apps/api/auth.py`; browser login test on PR #1 |
| 2 | Choose broker | Partial | Per-broker license, `compute_license(..., broker)` (#4). The Pocket Option referral rule applies only to Pocket Option. The portal has no broker picker yet; paper orders use the `kaos_paper` adapter. |
| 3 | Authorized market-data feed | **Works for crypto spot** | `apps/api/market_data.py`: Coinbase Exchange **public** ticker (`api.exchange.coinbase.com/products/{id}/ticker`), free, no account or key. `GET /api/v1/paper/quote/{symbol}`. **Stocks, options and forex: no licensed feed yet (returns 503).** Pocket Option has no public data API. |
| 4 | Charts: Free 1, Pro/Ultimate max 4 | Partial | Extension 1–4 selector limited by the server `chartLimit`; server `chartSlot` checks (403 `chart_limit`). Web portal and mobile have no multi-chart view. Four concurrent charts not performance-tested. |
| 5 | Unlimited watchlists, separate from active charts | Not built | No watchlist model yet. Will not count against `chartLimit`. |
| 6 | Strategy-mode signal | Partial | Extension strategies produce signals in Pocket Option; `/api/v1/trading/signal` records them. Not yet connected to market-data paper orders. |
| 7 | Paper order | Works | `POST /api/v1/paper/orders`, omitting `quote_price` |
| 8 | Simulated fill from a timestamped quote | **Works (crypto)** | BUY fills at the ask, SELL at the bid. The quote is fetched server-side at order time. The full quote (bid/ask/last, `quote_time`, `fetched_at`, `source`) is stored on the order as `execution_kind: market_data_paper`. Manually priced orders are labelled `manual_demo`. |
| 9 | Risk checks | Works | `kaos_risk_engine`: quote older than 10 s is refused; notional, exposure and position limits; kill switch; long-only. |
| 10 | Portfolio / trade journal | Works | Cash, positions, average cost, realized P&L; durable SQLite journal plus Mongo `paper_orders`/`paper_order_rejections`. |
| 11 | Persistence / reconnection | Works (book) | The book is rebuilt from stored orders on every request, and retries with the same `client_order_id` are idempotent. No live-streaming reconnect yet (quotes are polled every 5 s in the portal). |

## Known limits
- The ticker's `time` is the last trade time, so thin products whose last trade is over 10 s old are refused as stale. That is by design.
- One paper book holds both manual-demo and market-data fills. Each order is labelled, but P&L is not yet split by kind.
- Coinbase public market data is used under Coinbase's API terms for display and simulation only. Check the terms before any commercial redistribution.

## Tests
`apps/api/test_market_data_paper.py`: ticker parsing, ask/bid fills with provenance, stale-quote refusal, kill switch, idempotent retry without a second fetch, conflict 409, manual-demo label, book rebuild, and a 503 for asset classes without a feed.
