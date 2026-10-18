# Known gaps and open questions

## Needs founder input
1. **Which backend is live** on `api.tradingwithkaos.com`: the FastAPI/a2wsgi app (this repo), or the hand-written `wsgi_app.py` that `KAOS_REPAIRED` patches? The parent zip `KAOS_DEEPSCAN_AUTH_PARITY_CONTINUED_DEV.zip` is missing.
2. **Which extension version is in the Chrome Web Store.** Only the 1.7.12 Pro Terminal manifest has the `key` that pins ID `gbobopmnjgeeegniphckfpalhnebapjm`. The v1.7.11 baseline lacks it, so a store upload from it needs care.
3. **Branding:** the code uses "Trade With KAOS", TradeWithKAOS.com, and gold/red. The spec says tradingwithkaos.com, black/silver/electric-blue, and "Where We Give the Advantage to the Trader".
4. **Final pricing:** the code has monthly/yearly plans. The spec proposes Free/Pro/Ultimate.
5. GitHub repository target and hosting/deploy access.

## Technical gaps
- No original web build config. A CRA/craco config was reconstructed, so dependency versions are inferred.
- `apps/api/requirements.txt` pinned `websockets==16.1.1`, which conflicts with `coinbase-advanced-py` (<14). Relaxed to `>=13,<14`.
- REPAIRED's parity tests can't run because `kaos_berserker`/`berserker_fixtures` are missing.
- `content.js` still hard-codes legacy strategy labels (`7B`/`KAOS_BERSERKER`). REPAIRED's FIXES.md says this was fixed in the other runtime.
- Emergent platform dependencies: email proxy, Google OAuth, and the (now removed) analytics.
- No membership gating or receiver-based affiliate ledger in the API.
- Paper-order flow is not demonstrated end-to-end. The extension and mobile app are not run.
- Lint: 17 eslint warnings (unused vars, hook deps) in the web app.
