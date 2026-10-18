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
| 5 | Multi-broker support | Partial | Coinbase Advanced **read-only connection built** (`routes_broker_coinbase.py`: encrypted key vault, permission check, transfer-capable keys refused; balances, open orders, fills, fee tier, products) and shown on website, extension and Android. Not yet demonstrated against a real account. Coinbase order gateway (`routes_coinbase.py`) exists, disabled by `KAOS_COINBASE_LIVE_ORDERS`. Alpaca, IBKR, OANDA, Kraken, Tradier, tastytrade: not built. Pocket Option: extension DOM integration only, no API. | Demo read-only with a founder View-only key; then a shared adapter interface and the order lifecycle (preview/submit/cancel/reconcile) behind the disabled flag | Coinbase CDP View key (founder); other broker API accounts |
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
