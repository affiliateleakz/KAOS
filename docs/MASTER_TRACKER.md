# KAOS master development tracker

This tracker follows [`PRODUCT_VISION.md`](PRODUCT_VISION.md), the founder's authoritative scope document (2026-10-18). Each row maps to a section of that document.

**Status legend**
- **Works locally:** verified in this repo, with tests or a local run.
- **Partial:** some of it works locally, the rest is missing.
- **Code present:** imported from the archive but not verified end-to-end.
- **Missing:** not built.
- **Gated:** deliberately off until a founder, legal or validation sign-off.

Nothing in this file is deployed. "Works locally" never means "live in production".

| § | Requirement | Status | Where / evidence | Next step | External dependency |
|---|---|---|---|---|---|
| 2 | One account across site, extension and mobile | Partial | Cookie auth in `apps/api/auth.py`; the extension uses `/api/v1` device sessions | Mobile login against the same API | — |
| 3 | Public website | Partial | `apps/web` Landing (Free/Pro/Ultimate pricing), static `privacy.html` | Rebrand to black/silver/electric blue (decided); unverified figures removed in the claims PR | Hosting access, bot-protection allow-list |
| 3 | Member dashboard | Partial | `/dashboard/*`: subscription, affiliate ledger, paper trading, devices | Broker balances, positions and notifications cards | Broker APIs |
| 3 | Auth: email/password | Works locally | Login and `/me` tested in the browser | — | — |
| 3 | Auth: Google, verification, password reset | Code present | Uses the Emergent proxy | Replace with our own OAuth client and email provider | Google OAuth client; email provider (SES/Postmark) |
| 3 | Auth: MFA, device authorization | Partial | Device seats enforced via `deviceLimit` | TOTP MFA | — |
| 4 | Trading bot (extension, Pocket Option) | Code present | `apps/extension` v1.7.11 | Store resubmission. No AI-mode selector exists (hard-coded `STRATEGY`); autonomous AI fails closed and AI is advisory-only without server grant | Chrome Web Store; Pocket Option affiliate API |
| 4 | Chrome extension privacy compliance | Partial | PR #3: privacy policy, Collective Learning opt-in | Founder whitelists `/privacy.html` and resubmits | Host bot protection |
| 5 | Multi-broker support | Partial | Shared adapter registry `broker_adapters.py` (`GET /api/v1/brokers`). Coinbase Advanced: read-only account (balances, buying power, positions + P&L from fills, open orders, fills, fees) built and shown on website, extension and Android; **UNVERIFIED** against a real account. Order preview, cancel, order list, stop-loss/take-profit settings and account-wide limits built; real submission disabled (`KAOS_COINBASE_LIVE_ORDERS`). Alpaca, IBKR, OANDA, Kraken, Tradier, tastytrade: registered, not built (501). Pocket Option: extension only, no API. | Founder connects own View key via `docs/COINBASE_CONNECT_GUIDE.md`; then the next adapter | Coinbase CDP key (founder enters it in KAOS); other broker API accounts |
| 6 | Crypto / Stock / Options / Forex engines | Missing (paper only) | Paper book supports `CRYPTO_SPOT` long-only | Per-asset validation rules, then paper | Market data licenses |
| 6 | Pocket Option engine | Code present | Extension | Repair and validate on demo first | Pocket Option |
| 7 | KAOS Strategy, indicators, scoring | Code present, **audit FAIL** | `research/strategy_v2*`; v2.1 net negative on OTC data | Re-validate on licensed data; never market as profitable | Historical data |
| 8 | Strategy builder and backtesting lab | Partial | Research harness (CLI) | Portal UI over the backtester | Data |
| 9 | AI research engine (shadow) | Code present | FinBERT shadow, `/ai/predict` (research only) | Evaluation reports vs rule-based baseline | Model hosting |
| 10 | AI rules: Free none, Pro advisory, Ultimate AI/Both | Works locally (**gated**) | Pro: `aiInsights`, no AI modes. Ultimate AI modes locked until `POST /api/admin/ai-execution` records validation (audit-logged) | Independent validation sign-off | Independent reviewer |
| 11–16 | Market intelligence and scanners (stock/options/crypto/forex/social/news) | Partial | Opportunity radar and collectors (SEC etc.), gated to Pro/Ultimate via `entitlements.scanners` | Shared market-data layer | Data vendor licenses (Polygon, news, social APIs) |
| 17 | Ultimate signals (breakout, options, SPY 0DTE) | Missing | — | After §11 data and validation | Options data license |
| 18 | Portfolio management | Missing | — | Read-only broker balances | Broker APIs |
| 19 | Trade journal and analytics | Partial | Paper orders, realized P&L, rejections at `/dashboard/paper` | Journal notes, per-strategy stats | — |
| 20 | Android / iPhone apps | Code present | Expo starter 0.2.0, not run | Run against the local API | Apple/Google developer accounts |
| 21 | Memberships: Free $0, Pro $49, Ultimate $149, monthly only | Works locally | `DEFAULT_PLANS`, `FREE_ENTITLEMENTS`, `chartLimit` 1/4/4 enforced in the extension chart selector + strategy slots and server `chartSlot` checks (web/mobile have no multi-chart trading view; 4 charts not performance-tested), `deviceLimit` 1/3/5; tests in `test_membership_tiers.py` | Create Stripe prices `membership_pro_monthly`/`membership_ultimate_monthly`; financial validation of the prices | Stripe (founder) |
| 22 | 3-level receiver-based commissions | Works locally (preview) | `kaos.affiliate_ledger` + `services_affiliate_ledger.py`: renewals, refunds, chargebacks, idempotent | Downgrade adjustments; partial-refund mirror | — |
| 22 | Payouts, approval workflow | **Gated** | `PayoutsDisabled`; admin can't mark PAID | MLM/consumer-law review, KYC, tax | Legal counsel, payout provider |
| 22 | Affiliate dashboard (genealogy, ranks, resources) | Partial | Ledger card on the Affiliate page | Genealogy tree, L2/L3 lists | — |
| 23 | Rewards, Points & Gems | Missing | — | Phase 5 | — |
| 24 | Administration platform | Partial | Admin/moderation routes and pages; kill switches; audit log | Commission-rate config UI | — |
| 25–27 | Marketplace, community/academy, GOD MODE | Partial / Missing | Community page exists | Phase 5–6 | — |
| 28 | Security, risk, compliance | Partial | Paper-only default, risk limits, kill switch, gitleaks, secret removal (`SECURITY_AUDIT.md`) | Rate limiting, MFA, monitoring | — |
| 29 | Engineering: repo, CI, tests | Works locally | GitHub repo, CI (7 jobs), `make dev` | Backend monitoring | — |
| 31 | Phase 1: safe paper trading | Works locally | Simulated fills, positions, P&L, close-out, kill switch (PR #5) | Authorized quote feed | Market data license |
| 32 | Live trading | **Gated** | Coinbase live flag off; paper/shadow by default | Explicit founder authorization plus validation | Broker accounts |

## Founder decisions (2026-10-18, PR #6 comments)
- Charts: Free 1, Pro 4, Ultimate 4 concurrent trading charts (the earlier Ultimate 8 is withdrawn). Ultimate differentiates with premium signals, scanners and validated AI. The extension's 1–4 chart selector and the server now enforce the limit; four concurrent charts are not performance-tested yet.
- Pocket Option referral requirement: same policy for every tier, Pocket Option only, never imposed on other brokers. The API now applies it per broker and returns plain-language reasons; verification is a manual staff review of the submitted Pocket Option ID, not technical attribution. Still needed: broker-terms/legal confirmation and a fair path for existing Pocket Option accounts.
- Brand: dark/black + silver + electric-blue primary; gold/red only as restrained accents or semantic trading colours; keep KAOS logo assets; consistent across web, extension, Android, iOS.
- Marketing figures: remove all unverified win-rate/profit/return claims; only publish documented results with dates, live/paper/backtest provenance, costs and risk disclosures. No fabricated testimonials or screenshots.

## Open founder decisions
1. Privacy policy retention periods and support email.
2. Which live backend and which extension build to resubmit.

## Broker milestones (one per broker)

States, advanced only on evidence: planned → adapter_development → authentication_implemented → read_only_verified → order_management_tested → trading_approved (or temporarily_unavailable). Source of truth: `apps/api/broker_adapters.py` (`GET /api/v1/brokers`).

| Broker | Markets | State | Next milestone | Access needed |
|---|---|---|---|---|
| Coinbase Advanced | Crypto | authentication_implemented | read_only_verified: owner connects own View key (`docs/COINBASE_CONNECT_GUIDE.md`) | Owner's CDP View key, entered in KAOS |
| Pocket Option | Short-duration contracts | adapter_development | Repair extension integration (no public API) | Written permission for any API/automated access |
| Alpaca | Stocks, ETFs, crypto, options | authentication_implemented (read-only, simulated Alpaca only) | read_only_verified: owner connects a paper-account key on Broker Connections | Alpaca account + API key (paper account is free) |
| OANDA | Forex | planned | Adapter + practice-account auth | OANDA practice account + v20 token |
| Interactive Brokers | Stocks, options, forex, futures | planned | Client Portal gateway adapter | IBKR account + running gateway |
| Kraken | Crypto | planned | Adapter (no-withdraw key) | Kraken key without withdraw permission |
| Tradier | Stocks, options | planned | OAuth adapter (sandbox) | Tradier developer/sandbox account |
| tastytrade | Stocks, options, futures | planned | Open API adapter (sandbox) | tastytrade API access approval |
| MetaTrader 5 brokers | Forex, CFDs | planned | Bridge design per broker | MT5 broker permitting API/EA access |

## Live-execution safety (Priority 1, PR #11)
- Cancel, reconcile and exits of a verified position keep working with live disabled, consent expired or an emergency stop active; new BUYs are blocked by all of these. Tests: `test_coinbase_safety.py`.
- SELL exit lock (`EXIT_SUBMITTING`) is released when the intent cannot be saved, when Coinbase closes the SELL unfilled, or when a crash left a lock without an intent (worker, after 2 min; no exchange call is possible then). If the SELL's outcome is uncertain, the lock is kept: the worker looks the order up by client order id (all pages) and reconciles it if found; if it is absent from the listing, the order stays `UNKNOWN_RECONCILIATION_REQUIRED` with `NOT_IN_LISTING_MANUAL_REVIEW` after 10 min and is never auto-released. A broker timeout keeps the lock and marks the SELL `UNKNOWN_RECONCILIATION_REQUIRED`, so no duplicate exit is possible.
- Real-money execution remains disabled pending founder review.

## Alpaca adapter notes (PR stacked on #11)
- Connect: `PUT /api/v1/broker-connections/alpaca` {key_id, secret_key, environment: paper|live}; verified with `GET /v2/account` (must be ACTIVE); encrypted with the broker vault (same fields, so `broker_vault.py rotate` covers it).
- Read-only: `GET /alpaca/accounts` → account (cash, buying power, equity, PDT flags), positions (Alpaca's own avg entry / unrealized P&L), open orders, last 50 FILL activities. KAOS never calls an Alpaca order endpoint (Alpaca keys cannot be scoped read-only).
- Fees: no commission on US stocks/ETFs; SEC/FINRA TAF regulatory fees on sells appear as separate account activities (not yet itemised). Crypto has its own fee schedule (not built).
- Market hours: US equities 9:30–16:00 ET regular session, extended hours only for limit orders flagged extended_hours; to be enforced by the order layer when built.
- Not built: market data (needs an Alpaca data subscription choice: IEX free vs SIP), order preview/placement/cancel/reconciliation, extension and mobile screens.
