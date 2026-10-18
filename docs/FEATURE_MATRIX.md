# Feature matrix (truthful status)

Legend: **Works locally** = verified in this repo. **Code present** = source exists but has not been verified end-to-end. **Missing** = not implemented.

| Area | Feature | Status | Notes |
|---|---|---|---|
| Site | Landing, pricing, privacy, auth pages | Works locally | Branding still says gold/red "Trade With KAOS" (see Known gaps) |
| Portal | Login / register / me / logout (cookie) | Works locally | Demo users in dev only |
| Portal | Email verification / password reset | Code present | Needs an email provider. Currently the Emergent proxy |
| Portal | Google login | Code present | Uses Emergent OAuth |
| Billing | Stripe checkout + webhook | Code present | Monthly only: Free $0, Pro $49 (`membership_pro_monthly`), Ultimate $149 (`membership_ultimate_monthly`). Stripe prices not created yet; legacy `monthly`/`yearly` map to Pro/Ultimate |
| Membership | Free/Pro/Ultimate feature gating | Works locally | `get_entitlements` in the API. Free: Strategy-mode bot, 1 device, 1 chart. Pro: scanners and AI insights, 3 devices, 4 charts. Ultimate: premium, 5 devices, 8 charts. AI-controlled modes locked for all tiers until admin validation |
| Affiliate | Receiver-based 3-level commissions | Wired into API (preview only) | `services_affiliate_ledger.py` persists the kaos-core ledger in Mongo. Stripe checkout → initial, `invoice.paid` (subscription_cycle) → renewal, `charge.refunded`/`charge.dispute.created` → reversal. Member view: `GET /api/affiliate/ledger` + dashboard card; admin: `GET /api/admin/affiliate-ledger/{user_id}`. Not exercised against real Stripe events. |
| Affiliate | Payouts | Missing (intentionally) | Blocked until compliance review. Admin can no longer mark commissions `PAID` (403). |
| Trading | Paper order API (`/api/v1/paper/orders`, admin `/kill-switch`) | Works locally | Uses DurablePaperPipeline and the risk engine. Covers idempotency, conflict denial, notional/exposure limits, the kill switch, and an audit log. The quote price is supplied by the caller (no market feed yet). Simulated fills at that price, long-only average-cost positions, realized P&L, cash and close-out (`/positions/{symbol}/close`). Portal page `/dashboard/paper` |
| Trading | Coinbase live orders | Code present, disabled by flag | Must stay off |
| Research | Opportunity radar, collectors, FinBERT shadow | Code present, unit-tested | Collectors need API keys and authorized data |
| Research | Strategy v2/v2.1 | Unvalidated, audit FAIL | Must not be marketed as profitable |
| Extension | MV3 bot v1.7.11, cloud sync `/api/v1` | Code present | Pocket Option automation. Store ID continuity unresolved |
| Mobile | Expo starter 0.2.0 | Code present | Not run |
| Ops | One-command local stack | Works locally | `make dev` |
| Ops | CI | Added in this baseline | pytest + web build + gitleaks |
