# KAOS paper portal release candidate — safe publication

**Status: code integration candidate. Not yet deployed to cPanel.**
Never deploy the React build to `~/tradingwithkaos.com/index.html`:
that file is the existing cinematic Viking homepage. The member/admin SPA
belongs at `~/tradingwithkaos.com/portal/index.html`, with explicit
LiteSpeed rewrite rules for known member/admin routes only.

## 1. Verify GitHub build

The `.github/workflows/ci.yml` web job builds React, stamps the exact
commit in `build/kaos-build-revision.txt`, and uploads artifact
`kaos-react-portal-<commit>`.

Check:
- Python API, web, collectors, strategy and secret-scanner CI success.
- Website routes `/admin/trading-ops`, `/dashboard/paper`,
  `/dashboard/brokers`, `/dashboard/trading`, `/login`.
- No browser calls to the production Alpaca trading API.
- AI paper/live order flags remain **disabled** by default.
- Actual Alpaca Paper credentials must be entered only after reviewing
  the **paper** account details in KAOS, never in GitHub, chat or logs.

## 2. Deploy the matching Python API first, then the portal

After merge to `main`, update the local cPanel checkout to the exact latest\n`main` commit and run the reviewed `scripts/deploy-kaos-paper-api-cpanel.sh`\nunder the existing cPanel Python virtualenv. It validates/backs up the affected\nbackend modules, patches only the necessary two Alpaca router registrations\nin the existing `server.py`, preserves `passenger_wsgi.py` and `.env`, and\nsets the revision marker `kaos-paper-api-revision.txt`. Verify\n`https://api.tradingwithkaos.com/api/health` returns healthy before the\nReact portal step. If the API entrypoint or configured Python virtualenv\ndiffers, stop and review rather than guessing.\n\nOnly then use the **main push** GitHub Actions React artifact.
A PR artifact has a test-merge SHA, and must not be used in production.

In GitHub Actions → CI → successful **main** run, download its
`kaos-react-portal-<SHA>` artifact. Extract its contents to a **private**
directory on hosting: it must contain `index.html`, `static/`,
and `kaos-build-revision.txt` at the top level.

The portal release script verifies both the deployed Python API revision\nand the artifact revision exactly match
`origin/main`, snapshots the live homepage and `.htaccess`,
copies the compiled assets into `/static/`, publishes the SPA only to
`/portal/index.html` and adds known-route rewrites. No Python Passenger
restart and no modification to the original homepage.

**No automated cPanel access exists through this GitHub integration.**
A human/operator with hosting access must verify the actual cPanel document
root, current rewrite rules and API routing, then execute the reviewed
`scripts/deploy-isolated-kaos-portal-cpanel.sh` with
`KAOS_PORTAL_BUILD_DIR` pointing at the extracted artifact folder.

Never paste credentials in terminal arguments or issue logs. Keep the
`KAOS_ALPACA_PAPER_ORDERS_ENABLED` feature flag **off** on deployment.

## 3. Post-deploy browser smoke tests

1. Root `/`: existing Viking homepage remains visually unchanged.
2. `/login`: KAOS login appears, not a Viking-only fallback.
3. Authenticated `/admin/trading-ops`: trading operations screen loads;
   errors appear as errors rather than a silent blank page.
4. `/dashboard/brokers`: can display the **Alpaca Paper** connection
   panel; it does not accept live trading keys.
5. `/dashboard/paper`: the crypto candlestick chart, research signal
   preview, Alpaca Paper read-only account, paper stock chart and disabled
   manual paper beta are visible.
6. `/dashboard/trading`: four-chart terminal can select Alpaca Paper IEX
   stocks only when authenticated credentials exist.
7. `/api/health`: existing backend returns its health response; `/api`
   routing remains unchanged.
8. Account logs and browser console show no exposed private keys, uncaught
   JS errors or accidentally enabled AI/live orders.

If the site route or API behavior degrades, restore the backed-up
`.htaccess` shown by the installer. Do not overwrite the original
homepage while troubleshooting.

## 4. Actual paper trade qualification (not included in deployment)

- Connect a verified Alpaca **paper** API key using KAOS broker vault.
- Verify stock IEX quote freshness and availability during market hours.
- Run staged owner-only manual order preview/confirm at a small notional
  with paper order flag explicitly enabled **only after safety review**.
- Disconnect broker during network failure, then verify client-order-id
  reconciliation does not submit duplicate orders.
- Independently reconcile complete broker fills, initial position cost
  basis, fees, deposits, short positions and corporate actions; FIFO
  output is explicitly provisional gross P&L.
- Keep AI-to-paper bot **execution blocked** until independently reviewed,
  observed, and owner-authorized. This release is for interface and
  research validation, not profit claims.
