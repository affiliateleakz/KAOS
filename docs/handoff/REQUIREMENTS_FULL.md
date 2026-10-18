# KAOS FULL PLATFORM REQUIREMENTS — CROSS-CONVERSATION CONSOLIDATION

This is a product specification compiled from project discussions, not proof any feature is implemented. Most source archives are snapshots from differing points in time.

## Core principles
- Own website, extension, Android/iPhone, API and AI service; shared login/member entitlement; separate broker-specific execution adapters, not unrelated apps. Reuse shared KAOS strategy components where justified by testing.
- Project success: positive VERIFIED net returns if achievable, account growth with risk controls, and trustworthy transparent subscription business. Never guarantee that a sleeping user will profit. AI training independent of broker order execution.
- Put all source under founder's GitHub; reconcile extant KAOS 3.0 snapshots and earlier 1.7.x engine versions rather than overwriting them.

## Website
- tradingwithkaos.com; Chrome Store privacy-policy page directly linked; Terms, disclosures, billing, refunds, support@tradewithkaos.com, fb.com/tradingwithkaos.
- Cinematic hero with promo/video slot, anchored nav sections KAOS Bot / Features / Pricing / Results / FAQ; branded dark Viking aesthetic.
- Stripe test mode subscriptions with member entitlements, referral attribution, admin portal, affiliate dashboard and activity stats synced from bot.
- Secure signup/login Google and KAOS user account; login first, broker choice second. One browser login popup. Frontend must never contain broker PEM keys, PO SSIDs or AI model secrets.

## Extension
- Chrome MV3 store identifier gbobopmnjgeeegniphckfpalhnebapjm; preserve identity during update.
- Dashboard 1–4 charts recording simultaneously, per-chart strategy selector, independent candle TF, chart overlays, immediate historical backfill where legitimately supported, full-height Max, Mini, remove Mid, prevent cropped lower charts/overlaps.
- Left navigation Dashboard / Build Strategy (or Strategy Builder) / AI Lab / Diagnostics / Performance / Account. No charts rendered in unrelated tabs. Avoid redundant account/session displays and missing 'Follow us' links.
- Start button toggles Stop. No forced entry on startup, one active trade per market, one order per timestamp, no duplicate reversal entry, runner optional when supported, explicit BUY/SELL handling, accurate selected expiry. Maintain order lifecycle log and reasons per trade.
- Persist window/chart state and recover PO tab. Handle server/cloud outages honestly. Auto sync from broker only if supported by broker APIs and terms.
- Import/export saved strategy profiles, trade history/candles diagnostics CSV, versioned strategy catalogue, Pine import/backtesting only when actually implemented (otherwise label Coming Soon).

## Trading and research
- Stocks/ETFs, spot crypto, spot forex, options contracts, Pocket Option, futures/commodities eventually. Each instrument requires separate P&L, fees/ spreads/short or margin costs, market hours, settlement, tick size, risk models.
- KAOS Strategy: support/resistance, reversals, breakouts/retests, pullbacks, trend continuation, candlestick patterns. Direction/exit must be explicit and research-validated. Indicators such as EMA, SAR, Supertrend, ATR, ZigZag, volume, RSI etc can be studied; do not require all.
- Strategy scoring for Pro must be deterministic and explainable, score != probability. AI shadow/analysis cannot authorize or veto Pro orders. Ultimate AI vs Strategy vs Both only following evidence and approval.
- Proper source data, provenance, timestamps, OHLC integrity, no future leakage, walkforward holdouts not reused, executable next-bar timing, realistic filled prices, conservative intrabar ambiguity, order-size/slippage/transaction cost modeling, independent paper validation. Historical PO OTC candles cannot establish real-stock or exchange-crypto performance.
- Crypto test liquidity/order book imbalance, maker/taker, trend and breakout, higher-timeframe. Stocks test opening range, relative volume/strength, trend and pullback. Options test contract bid/ask, Greeks, strike, expiry, time decay, spread, assignment and 0DTE risk, not only underlying SPY price.
- Research data signed/secure, live vs historical, exchange market-data licensing and redistribution compliance.

## Brokers and trade lifecycle
- Current work includes Pocket Option and native Coinbase; consider Alpaca, Interactive Brokers and OANDA. Do not include OctoBot as trading runtime (founder rejected it). Self-hosted separate KAOS execution with paper mode default.
- Server confirms broker order states SIGNAL_GENERATED -> DELIVERY/RECEIVED -> ORDER_SUBMIT_ATTEMPT -> BROKER_CONFIRMED -> TRADE_OPEN -> TRADE_RESULT, with failed/disconnected/no-fill branches and idempotency.
- Account risk stop, max single-market position, session loss, stale quote rejection, kill switch, reconnection/resync. Show accurate true balances rather than fabricated demo balances.

## AI & scanners
- Separate AI research lab with timestamped training outcomes, model evaluations, shared anonymized permissible samples, model versioning, feature parity, shadow predictions, validation, drift detection, optional LightGBM/XGBoost/NN, server hosted inference.
- Stock, options, crypto, forex, news, earnings, economic, social sentiment, insiders and whale/watch, DEX, unusual volume, momentum, volatility and squeeze, Breakout/Follow-the-Money; watchlist notifications, performance and dashboards.
- Premium Stock Breakout and Options (SPY 0DTE) Signals; every signal must have entry, invalidation, exit/management, rationale and complete honest signal track record.

## Membership and affiliate
- Free $0: one chart, KAOS Strategy and common strategies, basic rule automation, no AI order authority.
- Pro $49 proposed: four charts, advanced deterministic scoring/strategies, backtest tools, stock/crypto/forex scanners and smart alerts, AI analysis only. NO 'AI vs Strategy vs Both' controls.
- Ultimate $149 proposed: Pro + advanced scanners, Ultimate Signals, options analysis, validated AI order authority, Strategy vs AI vs Both control after approval.
- Affiliate earnings by receiver tier at respective upline distance: Free 10/0/0%, Pro 30/15/0%, Ultimate 50/25/5%; recurring on eligible subscriptions, no reward solely for recruiting. Ledger, genealogy, refunds, pending and paid, ranks, points/gems, anti-fraud/KYC/tax, admin-configurable for future changes (protect locked rates and historical transactions). Highest payout sum 80% and must model unit economics.
- GOD MODE hypothetical future feature: affiliate broker links/white-label; KAOS receives possible 5% only after basis and permissions/legal review.

## Mobile
- Separate Android and iOS app deliverables based on Expo React Native starter when feasible. Shared accounts/permissions, user experience for watchlists, alerts, scanners, charts, account balances, risk killswitch and monitoring, secure broker link, detailed strategy/signal views; background execution server not on mobile.
- Publishability checklist includes Apple Developer and Google Play Console access, privacy disclosures, signing/test accounts, store screenshots, mobile purchase policies, push permissions and release review.

## Defects from past conversations to explicitly audit
- Persistent KAOS CLOUD OFFLINE, login verifying failure, duplicate sign-in windows, mismatched API hosts, OAuth callback/session errors, bad CORS methods, server Mongo timeout, OPENAI BRAINSERVER REQUIRED endpoint absent, XGB/LightGBM frozen at 50%, JS duplicate identifier ALPHABOT_V194, undefined candidate signal, charts blank, candles not moving, warmup blocking trades, duplicate auto payout, wrong expiry (60s when 15s selected), stale dashboard balances, inconsistent labels and tab placements, 4th chart cropped, missing build-strategy page, incorrect extension icon and Chrome Store policy rejection.
- Preserve Chrome Store privacy-policy fix and do not fake Google sign-in, broker connect or backfill by dummy UI responses.
