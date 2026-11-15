# Known gaps and open questions

## Needs founder input
1. **Which backend is live** on `api.tradingwithkaos.com`: the FastAPI/a2wsgi app (this repo), or the hand-written `wsgi_app.py` that `KAOS_REPAIRED` patches? The parent zip `KAOS_DEEPSCAN_AUTH_PARITY_CONTINUED_DEV.zip` is missing.
2. **Which extension version is in the Chrome Web Store.** Only the 1.7.12 Pro Terminal manifest has the `key` that pins ID `gbobopmnjgeeegniphckfpalhnebapjm`. The v1.7.11 baseline lacks it, so a store upload from it needs care.
3. **Branding — decided 2026-11-14:** gold/brown is the canonical identity. The black/silver/electric-blue "spec" that PRs #13 and #14 applied is retired; those two PRs have been reverted and the gold palette (`--kaos-gold:#d4af37`, `--primary: 46 65% 52%`) is back across the site. Do not reintroduce the blue/silver palette.
4. **Final pricing:** the code has monthly/yearly plans. The spec proposes Free/Pro/Ultimate.
5. GitHub repository: `affiliateleakz/KAOS`. Hosting/deploy access is still outstanding.

## Technical gaps
- No original web build config. A CRA/craco config was reconstructed, so dependency versions are inferred.
- `apps/api/requirements.txt` pinned `websockets==16.1.1`, which conflicts with `coinbase-advanced-py` (<14). Relaxed to `>=13,<14`.
- REPAIRED's parity tests can't run because `kaos_berserker`/`berserker_fixtures` are missing.
- `content.js` still hard-codes legacy strategy labels (`7B`/`KAOS_BERSERKER`). REPAIRED's FIXES.md says this was fixed in the other runtime.
- Emergent platform dependencies: the email proxy, and a legacy `POST /api/auth/google/session`
  route. Google sign-in for the web no longer needs Emergent — `POST /api/auth/google/credential`
  verifies a Google ID token directly; the old session route is now unused and should be deleted
  once no deployed client calls it.
- Pricing (founder decision 2026-10-18): monthly billing only — Free $0, Pro $49/mo, Ultimate $149/mo. Yearly is retired; legacy `monthly`/`yearly` plan ids map to Pro/Ultimate. Stripe prices are created at checkout from these amounts (no live Stripe change made).
- Free tier (founder decision 2026-10-18): bot in STRATEGY mode on 1 device, no AI modes/scanners/premium tools. The extension license no longer requires a paid membership, but still requires a verified Pocket Option affiliate account and an unsuspended account. AI endpoints (`routes_ai`, FinBERT) still require an ACTIVE paid membership.
- Recipient tier is the sponsor's tier when the payment is recorded; members who are not ACTIVE/TRIAL count as Free (10% L1 only).
- Partial refunds reduce the ledger, but the legacy `commissions` mirror only flips to REVERSED on full reversals.
- Membership gating uses the existing per-plan `entitlements`; the kaos-core `PERMISSIONS` map (free/pro/ultimate) is not yet the source of truth.
- Paper-order flow is not demonstrated end-to-end. The extension and mobile app are not run.
- Lint: 17 eslint warnings (unused vars, hook deps) in the web app.
- **Unsubstantiated performance claims on the homepage:** the hero mockup shows "78.6% win rate", "+$542.30", and "25,287 trained samples". Nothing in the handoff backs these up, and the v2.1 audit is net negative. Remove them or label them as illustrative before going public (compliance).

- Paper trading (simulated): BUY/SELL fill immediately at the member-entered quote price; long-only average-cost book with realized P&L, cash and position close-out. No authorized quote feed, so these are not market fills; unrealized P&L is only shown at a price the member types in. Closing a position is blocked while the emergency stop is active (risk engine behaviour).

- AI-controlled trading (spec §10): AI and Strategy+AI modes are locked for every tier, Ultimate included, until an admin records independent validation (`POST /api/admin/ai-execution {validated, note}`, audit-logged; setting `ai_execution_validated`, default off). The extension stores the server entitlements (`kaosEntitlements`) at startup and only allows its local autonomous-AI execution path when `aiExecutionLocked === false` and `modes` includes `AI` (fails closed when unknown). Without that entitlement the legacy AI controller (`aiCtrlApply`, not on the live execution path) is advisory-only and cannot place, veto or override a strategy trade. Chart limits: Free 1, Pro 4, Ultimate 4 (founder decision 2026-10-18: Ultimate differentiates with signals, scanners and validated AI, not chart count) — `chartLimit` entitlement. Enforced in the extension popup's 1–4 chart selector (options above the plan are disabled; unknown entitlements fail closed to 1), in the content script's per-chart strategy slots, and server-side via optional 0-based `chartSlot` on `/api/v1/trading/intelligence|signal|execution` (403 `chart_limit`) and `chartSlot` in `/api/v1/trading/events` payloads (rejected `chart_limit`). Four concurrent charts are not yet performance-tested; the web dashboard and mobile have no multi-chart trading view.
