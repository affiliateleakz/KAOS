# KAOS release artifacts and launch gates

## Download artifacts from GitHub Actions
1. Open the latest **successful** CI run for draft PR #54.
2. Under **Artifacts**, download `kaos-website-build` and `kaos-chrome-extension-zip`. Artifacts expire after 14 days.
3. Deploy the extracted website build to a **staging** static host with SPA route fallback; configure API origin, TLS and secrets on the backend separately. The website artifact does not contain a deployed backend.
4. Test `https://<staging-host>/privacy.html`, login, memberships, dashboard, backend health and API routing before considering production.
5. Unzip the Chrome artifact for local unpacked testing or submit the ZIP through the existing Chrome Web Store listing. The current manifest version is **1.7.11**; verify the extension ID and signing/update continuity for the existing listing `gbobopmnjgeeegniphckfpalhnebapjm`. Do not assume the source tree/ZIP by itself proves the same extension ID.

## Hard release blockers
- Complete the known billing cancellation CSRF, revoked device re-registration, missing v1 login lockout, and v1 sync mass assignment security fixes and regression tests.
- Verify free/paid access, account sign-in, billing and cancellation on staging.
- Complete staging smoke tests: website authentication -> broker selection -> extension authentication -> verified data feed -> paper trading/replay -> logout/sign-in. Test four-chart entitlements.
- Verify privacy-policy link responds 200 and matches Chrome Web Store disclosures.
- Confirm production backend/runtime parity. The live backend and existing Web Store extension version are currently unverified.
- Confirm provider credentials/data rights. Broker choice, model catalog entries, and collector code are **not** proofs of live operational integrations. Keep AI-controlled and real-money trading disabled until separately authorized and validated.

## CI scope
CI builds the frontend and validates extension file/syntax presence; it cannot prove visual appearance, browser behavior, production connectivity, live signals or trading profitability. The extension ZIP is a packaging artifact, not certification for production release.
