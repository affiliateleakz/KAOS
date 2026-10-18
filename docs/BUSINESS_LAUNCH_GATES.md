# KAOS Business Launch Gates

Status: development checklist, not a claim of production readiness. Maintained for the founder. Completion requires observable evidence, not unchecked feature labels.

## Critical release blockers (must close before paid launch)

- [ ] Merge the ordered PR stack with clean CI, protected main branch, code-owner review, rollback strategy, and staging deployment. PR #12 is stacked on #11; do not deploy a dependent branch directly.
- [ ] Publish working privacy policy, terms, billing and refund terms, service contact, data-retention and broker permission disclosures. Get legal review for regulatory positioning and financial promotions.
- [ ] Verify Free / Pro ($49 monthly) / Ultimate ($149 monthly) entitlement boundaries on server endpoints and clients; validate upgrade, downgrade, cancellation, failed payments and grace-period behavior.
- [ ] Stripe production account/webhook signature validation, reliable event-idempotency and reconciliation; conduct refund/chargeback/affiliate clawback tests. No production Stripe changes without founder approval.
- [ ] Test affiliate tiers and payout ledger accounting under duplicate events, reversals and disputes; approve disclosures and payout compliance.
- [ ] Real customer sign-in with Google and password, refresh/logout/device revocation, subscription enforcement, scoped admin roles and audit records. Test account isolation and unauthorized request behavior.
- [ ] Complete broker self-service connect/rotate/revoke UI and encrypted vault; no API secrets in source, console, client persistence, PRs, or support tickets.
- [ ] Validate real account balances, positions, order state and reconciliation with actual authorized broker test accounts; keep unsupported providers clearly marked.
- [ ] Security review including session handling, CORS, CSRF, rate limiting, dependency scanning, vault rotation, database backups, restoration and incident playbook.
- [ ] Staging and production monitoring: health, latency, quote freshness, broker outages, order anomalies, payment reconciliation, privacy-safe logs and alerts.
- [ ] Finalize Chrome Store permissions, privacy declaration and review; sign and test Android/iOS releases on actual devices; verify websites and mobile deep links.

## Real-money trading activation (separate gate; disabled until all pass)

- [ ] Brokerage API contract and commercial permissions independently verified per asset class and region.
- [ ] Correct account ownership, permission scopes, trading hours, minimum sizes and precision verified.
- [ ] Conservative per-user and per-account risk limits, position sizing, balance checks, kill switch and approval UX.
- [ ] Idempotent submit, durable intent-before-send, restart recovery, and broker reconciliation under timeout, crash, partial fill and reordered events.
- [ ] Never release uncertain order or position locks merely because a paginated order-list query fails to find an order.
- [ ] Cancel / close paths independently functional during emergency stop; audit owner confirmation and expiry/revocation.
- [ ] No unvalidated strategies or AI allowed to place real orders; shadow trading and unbiased backtests have separate acceptance evidence.
- [ ] First controlled tiny live execution performed only after the founder's explicit broker/account-specific confirmation, with verified cancellation, fill and ledger reconciliation.

## Product completion gates

- [ ] One to four independent charts with server-side membership limits, watchlists, indicators, chart replay, immutable candle provenance and source/freshness display.
- [ ] Real broker-supported chart candles integrated only where access and licensing allow; no synthetic or cross-broker quotes presented as broker-specific.
- [ ] Website, extension, Android and iPhone share broker connections, chart settings, portfolio truth and authorization.
- [ ] Clear Free / Pro / Ultimate feature matrix, checkout/onboarding, upgrade prompts and member portal.
- [ ] Strategy Builder, KAOS AI Lab and backtesting with reproducible fixtures, walk-forward and out-of-sample reporting; no guaranteed returns claims.
- [ ] Admin console for users, memberships, feature flags, audits, incidents, API health and access revocation.
- [ ] Market intelligence, social/SEC monitoring, options and SPY 0DTE advisory signals labeled by quality and availability; do not equate an illustrative 1000% return with an achievable result.
- [ ] User acceptance testing, accessibility, support workflows, feedback, performance checks and customer-facing release notes.

## Current evidence (2026-10-18)

- Broker discovery and read-only Alpaca/OANDA account routes, site/mobile/extension broker panels, and server-stored chart settings are under review on PR #12.
- PR #11 Coinbase execution has had simulation-based safety testing, not real-account acceptance.
- CI verifies a subset of these behaviors; it does not prove operational broker readiness, secure production deployment or payment readiness.
- Real trading is disabled; no PR in this stack has been merged or deployed by this workflow.

Keep this checklist current with links to tests, release artifacts and reviewed approvals as gates are satisfied.
