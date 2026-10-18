# KAOS Trading 3.0 — Chrome Web Store Privacy & Permissions Review

## Implemented in this development package

- Public static Privacy Policy at `site/tradingwithkaos.com/frontend/public/privacy/index.html`. Hosting the React build as static assets exposes `https://tradingwithkaos.com/privacy/` without SPA history-rewrite support.
- React route `/privacy` and `/privacy/`, for navigation within the website.
- Links in the website landing footer, authenticated member dashboard, Chrome extension footer, and mobile Account & Alerts page.
- Scope includes account, membership, Google sign-in, connected brokers, trading records, browser extension operations, locally stored data, AI/research features, Stripe billing, service providers, retention/access/deletion, security, and Limited Use disclosure.

## Before resubmission — REQUIRED HUMAN/PRODUCTION CHECKS

1. Publish the updated built website at `https://tradingwithkaos.com/privacy/` and verify it returns HTTP 200 **without sign-in**, on desktop and mobile. Source code alone is not a live page.
2. Enter that *exact live URL* in the **Chrome Web Store Developer Dashboard → Privacy practices → Privacy Policy** field. A link in the extension or listing description alone is insufficient.
3. Review every factual privacy statement with the business owner and service administrators. Specifically verify: actual hosts and processors, which third-party AI services receive data, production secret encryption, access controls, diagnostic uploads, analytics, data retention periods, account deletion process, affiliate data handling, all user-facing disclosures/consent, and that the support mailbox works. This draft does not certify these controls are deployed.
4. Update the Privacy practices questionnaire to truthfully disclose collection/use of personal identifiers, authentication, financial/trading information, website content, browsing-site data associated with supported broker sites, and usage or diagnostics as applicable. Confirm each category against live behavior.
5. Confirm Google OAuth scopes and whether a Google APIs Limited Use statement and prominent disclosure/consent flows are required for enabled functionality.
6. Review the extension background's `collectiveLearning` setting: its current fallback appears to treat absence of a saved preference as enabled. Verify prominent notice and genuine opt-in before collecting or sharing user-specific trading outcomes for cross-user training.
7. Review **minimum permissions**: current manifest requests `storage`, `unlimitedStorage`, `activeTab`, `scripting`, `tabs`, `alarms`, `downloads`, `nativeMessaging`, `identity`; host access covers multiple Pocket Option domains, KAOS API/website domains, local research ports, and other domains. Remove any permission or host not required by shipped functionality. Do not remove blindly because doing so may break existing features.
8. Review single-purpose listing explanation: extension's primary purpose is connected trading assistance on supported trading platforms; clearly describe what trading pages it accesses and what data flows to KAOS cloud.
9. Check that API keys/tokens are not exposed in page source, extensions, logs, build artifacts, or developer console; backend credential encryption must be independently verified.
10. Confirm your privacy and data handling implementation respects Chrome Web Store User Data and Limited Use requirements, including encryption in transit and restrictions on selling/using extension user data for advertising.
11. Resubmit only after testing the actual signed extension package and the rejection email's exact policy violation. A privacy page **does not guarantee** acceptance; Google may reject for additional reasons.

## Google policies (verify current version before submission)

- https://developer.chrome.com/docs/webstore/program-policies/policies
- https://developer.chrome.com/docs/webstore/user_data
- https://developer.chrome.com/docs/webstore/troubleshooting

### Rejection-specific note

The exact Google rejection text was not provided here. We **cannot attribute the rejection solely to the missing privacy page**. This build addresses the page/link portion of the privacy policy requirements; production deployment and compliance audit remain separate tasks.
