# KAOS Trading Bot — Chrome Web Store rejection fix

**Extension item ID:** `gbobopmnjgeeegniphckfpalhnebapjm`
**Rejection:** User Data Privacy — “Privacy policy link does not lead to a valid privacy policy”
**Reviewer reference:** Purple Nickel; routing ID FZSL.

## Fix included in this development source

- Standalone public Privacy Policy HTML: `site/tradingwithkaos.com/frontend/public/privacy/index.html`.
- Public React page route: `/privacy` and `/privacy/` (not behind sign-in).
- Website home, login, member dashboard links to `/privacy/`.
- Chrome extension popup and mobile settings links to `https://tradingwithkaos.com/privacy/`.
- Full review checklist: `CHROME_WEB_STORE_PRIVACY_REVIEW.md`.

## Fastest independent website deployment (cPanel)

1. Download the separate `KAOS_PRIVACY_PAGE_CPANEL_UPLOAD.zip` companion package.
2. Open cPanel → File Manager → the **actual document root for tradingwithkaos.com** (often `public_html`, but verify).
3. Extract `privacy/index.html` **at the document root**, yielding `<document-root>/privacy/index.html`. Do not nest it under another `public_html` folder.
4. Confirm that `https://tradingwithkaos.com/privacy/` is public, gives HTTP **200**, contains the heading “Privacy Policy”, and does **not** redirect to the homepage or require login. Check in a private browser window and on mobile; test both with and without trailing slash.
5. Test the support email address and verify the Privacy Policy text accurately matches production behavior before publishing. In particular, check AI sharing consent, connected brokers, account deletion, third-party service providers, diagnostics and credential handling. This is a tailored draft, **not legal approval**.
6. Chrome Web Store Developer Dashboard → **KAOS Trading Bot** (`gbobopmnjgeeegniphckfpalhnebapjm`) → **Privacy practices** → **Privacy Policy** field: `https://tradingwithkaos.com/privacy/`. Save and resubmit the revision.
7. Make the Privacy practices user-data disclosures consistent with the **actual** submitted extension build and the policy. Google's review may identify additional issues; a working URL fixes only the reported problem.

**Do not** submit a homepage, dashboard, login page, local `file://` path, or an unbuilt `src/` React route as the policy link. The privacy page must be deployed to an independently accessible web URL.

Sources: https://developer.chrome.com/docs/webstore/troubleshooting and https://developer.chrome.com/docs/webstore/program-policies/policies
