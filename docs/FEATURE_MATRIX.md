# Feature matrix (truthful status)

Legend: **Works locally** = verified in this repo. **Code present** = source exists but has not been verified end-to-end. **Missing** = not implemented.

| Area | Feature | Status | Notes |
|---|---|---|---|
| Site | Landing, pricing, privacy, auth pages | Works locally | Branding still says gold/red "Trade With KAOS" (see Known gaps) |
| Portal | Login / register / me / logout (cookie) | Works locally | Demo users in dev only |
| Portal | Email verification / password reset | Code present | Needs an email provider. Currently the Emergent proxy |
| Portal | Google login | Code present | Uses Emergent OAuth |
| Billing | Stripe checkout + webhook | Code present | Plans are monthly $29 / yearly $279, **not** Free/Pro/Ultimate $0/$49/$149 |
| Membership | Free/Pro/Ultimate feature gating | Missing in API | Prototype exists in `packages/kaos-core` |
| Affiliate | Receiver-based 3-level commissions | Missing in API | `routes_affiliate` is single-level and flat-rate. Prototype calculator exists in kaos-core. No ledger, refunds, or renewals |
| Affiliate | Payouts | Missing (intentionally) | Blocked until compliance review |
| Trading | Durable paper pipeline, broker registry | Code present, unit-tested | Not demonstrated end-to-end |
| Trading | Coinbase live orders | Code present, disabled by flag | Must stay off |
| Research | Opportunity radar, collectors, FinBERT shadow | Code present, unit-tested | Collectors need API keys and authorized data |
| Research | Strategy v2/v2.1 | Unvalidated, audit FAIL | Must not be marketed as profitable |
| Extension | MV3 bot v1.7.11, cloud sync `/api/v1` | Code present | Pocket Option automation. Store ID continuity unresolved |
| Mobile | Expo starter 0.2.0 | Code present | Not run |
| Ops | One-command local stack | Works locally | `make dev` |
| Ops | CI | Added in this baseline | pytest + web build + gitleaks |
