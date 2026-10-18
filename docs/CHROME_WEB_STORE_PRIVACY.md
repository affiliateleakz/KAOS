# Chrome Web Store privacy rejection (Purple Nickel) — findings and resubmission checklist

Rejection: draft v1.0 of item `gbobopmnjgeeegniphckfpalhnebapjm`, Oct 14 2026, "Privacy policy link does not lead to a valid privacy policy (Owner sites are not considered valid privacy policies)".

## What was observed (2026-10-18, read-only requests)

| Request | Result |
|---|---|
| `curl https://tradingwithkaos.com/privacy/` (normal browser UA, datacenter IP) | Redirected to `recaptcha.cloud` "Human verification" page — no policy. Same for `/`, `/privacy`, `www.` and `api.tradingwithkaos.com/api/health`. |
| Same URL with Googlebot UA (challenge skipped) | 200, but the body is the SPA shell `<title>KAOS Trading — Trade With KAOS</title>` (3.3 KB, no policy text). |
| `https://tradingwithkaos.com/privacy/index.html` | Same SPA shell — the static policy file is not deployed. |
| Live JS bundle `main.b7453735.js` | Contains only a "Privacy Policy — How we handle your data." card; no policy text. Still loads `assets.emergent.sh/scripts/emergent-main.js`. |

So a reviewer following the link gets either a bot challenge or the homepage — exactly "owner site, not a privacy policy".

## Fixes in this repo

- `apps/web/public/privacy.html`: standalone static policy (no JavaScript needed), rewritten to match what the Extension actually does (derived from `apps/extension` source: `kaos-cloud.js`, `kaos-sync-client.js`, `kaos-learning-client.js`, `content.js`, `background.js`, `manifest.json`).
- `apps/web/public/.htaccess`: serve real files/directories before the SPA fallback so static files such as `/privacy.html` are served before the SPA on Apache/cPanel.
- `apps/web/src/pages/Privacy.jsx`: in-app `/privacy` route hard-redirects to the static page (single source of truth).
- `apps/extension/background.js`: Collective Learning samples are sent only after explicit opt-in (`collectiveLearning === true`); previously sent unless turned off. The server already requires `collective_learning_consent` (`routes_ai.py`).
- `scripts/check_privacy_url.sh [URL]`: fails if the URL serves a bot challenge, SPA shell or lacks the Limited Use section.

## Resubmission checklist (founder actions — not done by Devin)

1. Deploy the web build so `build/privacy.html` and `build/.htaccess` are on the host.
2. Exempt `/privacy.html` (ideally the whole site and `api.`) from the host's "Human verification" bot challenge (cPanel / Imunify360 / hosting firewall). The API being challenged would also break the Extension for users whose IP is flagged.
3. Run `scripts/check_privacy_url.sh https://tradingwithkaos.com/privacy.html` from outside the host; it must print `OK`.
4. In the Developer Dashboard → Privacy practices: set Privacy policy URL to `https://tradingwithkaos.com/privacy.html` and declare data types consistent with the policy:
   - Personally identifiable information (email, name), Authentication information (password at login, tokens);
   - Financial and payment information (account balance read on page, trade amounts/P&L; Stripe subscription status);
   - Website content (prices/candles/trade results on Pocket Option pages); User activity (trade events).
   - Certify: not sold, not used for unrelated purposes, not used for creditworthiness/lending.
5. Justify each permission (text is in section 4 of the policy). Consider removing unused ones before resubmitting.
6. Confirm the business details in the policy: retention (24 months / 90 days logs), contact `support@tradewithkaos.com` (domain differs from tradingwithkaos.com), and that the Collective Learning toggle (member dashboard → KAOS AI) is the only opt-in path; the Extension now syncs that consent from `/bot/config`.

The submitted draft was v1.0; this repo's Extension is v1.7.11 and lacks the manifest `key` that pins the store ID (see `docs/KNOWN_GAPS.md`).

## Update 2026-10-18
The founder uploaded the policy as `https://tradingwithkaos.com/privacy.html`; the repo now uses that path everywhere (site links, Extension popup link, canonical URL). Verified: with the bot challenge bypassed it serves this exact file (9,271 bytes, "Effective October 18, 2026"). From a normal browser user agent on a datacenter IP it still redirects to the `recaptcha.cloud` challenge, so step 2 above is still required.
