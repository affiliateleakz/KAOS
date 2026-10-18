# KAOS Trading 3.0 development source — v0.8 status

**New in this package**

- Research-only option-volume increase monitor (`collectors/options_activity.py`) and data-source health identifier (`option-volume-rise`).
- Integrated into opt-in collector runner; save baseline state only when all submitted evidence is acknowledged by KAOS API; dry run does not advance.
- Local-only congressional disclosure CSV review utility (not ingested into paid KAOS feed). Official source URLs and transaction/filing dates are checked; original filings are not independently verified by the utility.
- Website Opportunity Radar and Android/iPhone development source include options activity and congressional review notices.
- The most recent v0.7.1 KAOS website Privacy Policy at `/privacy/`, and its Auth/Landing/Dashboard navigation links, are retained.
- No Unusual Whales code, provider account, subscription, or user-facing paywall has been reintroduced.

**Retained**

Existing source trees for extension, backend, website, mobile, collectors, and trading-engine modules; existing broker order execution code is unchanged in this build.

**Validation**

- Collector unit tests: 69 passed.
- Backend opportunity/health-related tests: 10 passed.
- Python bytecode compilation: passed.
- Website JSX and mobile TSX parser checks: passed on 7 changed files (syntax only).
- ZIP integrity: verified.

**Not verified / not completed**

- Tradier API requests with a real account, API entitlements, network restrictions, and commercial distribution authorization.
- Full website deployment, browser builds, Android/iOS native builds, or running on a physical device.
- Live order and broker execution integration, membership flows, production database migrations, push notifications.
- Automatic congressional trading feed (intentionally excluded due to commercial-use restrictions).
- Other promised KAOS 3.0 features remain in development; this package is not the complete final system.

**Deployment**: None. Install only after backup and staging review. Do not replace live files without checking against the current deployed versions. Keep tokens server-side.
