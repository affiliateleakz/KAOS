# KAOS 1.7.1 Multi-broker selector foundation

Built on supplied KAOS 1.7 AI Research Foundation ZIP. Preserves Pocket Option trading implementation and existing login, dashboard, and membership behavior. After the existing dashboard loads, first-time users see only a broker choice; selecting Pocket Option resumes existing KAOS. Users can change broker with the bottom-right control.

**IMPORTANT: Coinbase, Kraken, and Interactive Brokers are displayed as future connection options only.** Selecting one explicitly reports that broker API authentication, market-data streaming, account discovery, paper/live selection, and order execution are NOT implemented. It cannot send real or paper trades to those brokers. This is a UI foundation, not a finished multi-broker integration. Do not use it as a real-money exchange bot.

No broker API keys, OAuth credentials, trading endpoints, or order permissions were added. The existing Pocket Option trading system was left unchanged. Non-Pocket Option choices intentionally cannot be persisted as connected accounts.

To complete: implement broker-specific secure authentication, server-side credential management, REST/WebSocket adapters, order lifecycle, account-type detection, paper simulator where unavailable, live-trading authorization, reconciliation, and broker-specific risk controls. Validate against sandbox/test accounts before real orders.
