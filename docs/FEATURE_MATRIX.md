# Feature matrix (truthful status)

Legend: **Works locally** = verified in this repo. **Code present** = source exists but has not been verified end-to-end. **Missing** = not implemented.

| Area | Feature | Status | Notes |
|---|---|---|---|
| Site | Landing, pricing, privacy, auth pages | Works locally | Branding still says gold/red "Trade With KAOS" (see Known gaps) |
| Portal | Login / register / me / logout (cookie) | Works locally | Demo users in dev only |
| Portal | Email verification / password reset | Code present | Needs an email provider. Currently the Emergent proxy |
| Portal | Google login | Code present | Uses Emergent OAuth |
| Billing | Stripe checkout + webhook | Code present | Plans are monthly $29 / yearly $279, **not** Free/Pro/Ultimate $0/$49/$149 |
| Membership | Free/Pro/Ultimate feature gating | Library only (`kaos.affiliate_ledger.has_permission`) | Not wired into the API yet. The `ai_execution` permission does **not** grant order authority |
| Affiliate | Receiver-based 3-level commissions | Library + tests (`packages/kaos-core/kaos/affiliate_ledger.py`) | Covers idempotency, renewals, rate snapshot per payment, full/partial refunds and chargebacks, a hold period, cycle rejection, and disabled payouts. Not wired into the API: `routes_affiliate` is still single-level and flat-rate |
| Affiliate | Payouts | Missing (intentionally) | Blocked until compliance review |
| Trading | Paper order API (`/api/v1/paper/orders`, admin `/kill-switch`) | Works locally | Uses DurablePaperPipeline and the risk engine. Covers idempotency, conflict denial, notional/exposure limits, the kill switch, and an audit log. The quote price is supplied by the caller (no market feed yet). No fills or P&L simulation. No portal UI |
| Trading | Coinbase live orders | Code present, disabled by flag | Must stay off |
| Research | Opportunity radar, collectors, FinBERT shadow | Code present, unit-tested | Collectors need API keys and authorized data |
| Research | Strategy v2/v2.1 | Unvalidated, audit FAIL | Must not be marketed as profitable |
| Extension | MV3 bot v1.7.11, cloud sync `/api/v1` | Code present | Pocket Option automation. Store ID continuity unresolved |
| Mobile | Expo starter 0.2.0 | Code present | Not run |
| Ops | One-command local stack | Works locally | `make dev` |
| Ops | CI | Added in this baseline | pytest + web build + gitleaks |
