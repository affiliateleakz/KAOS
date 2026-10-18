# KAOS ANDROID + IPHONE APPLICATION SPEC

## Deliverable
A single maintained React Native / Expo codebase producing supported iOS and Android binaries, native-feeling UX, plus web dashboard/Chrome extension for desktop trading. Existing starter ZIPs at mobile_snapshots/ are a baseline candidate ONLY; audit dependencies and evaluate what works.

## MVP flow
1. Splash and secure login via KAOS account or supported Google sign-in; shared backend session and tier entitlement.
2. Dashboard: account/broker connection status, watchlist performance, AI advisory availability, latest signal and current paper positions, trading system health.
3. Screens: Home, Markets & Scanners, Watchlists, Signals, Positions & Journal, Bot Control, Membership, Affiliate, Profile/Settings.
4. Remote bot management: start/stop eligible paper strategies, monitor orders, change account-level risk rules only with verified authorization; server continues when phone sleeps. Always emergency kill and disconnected states.
5. Push notifications (opt-in): order placed/failed, account risk trigger, validated alert, broker disconnected, subscription notice; no misleading 'guaranteed win' alerts.
6. Broker connections via secure PKCE/OAuth or broker sanctioned consent on server; never paste private key into mobile app logs; credential revocation and rotation.
7. Tier gating Free/Pro/Ultimate exactly as website; no AI-order mode in Free/Pro. Affiliate dashboard including levels and ledger but NO automated payouts until approved.
8. Controls for paper/live clearly distinguish availability; legal and regulatory approvals and testing before enabling live. No trading dependent on Android accessibility hacks or iOS foreground running.

## Engineering acceptance
- Share typed API contracts and user identity with website and Chrome extension; handle offline states gracefully.
- Secure token storage, TLS, permission minimization, optional biometric unlock, analytics/privacy preference controls, no secrets hardcoded or embedded in build.
- Unit/integration/e2e tests on current Android/iOS simulators, responsive layouts, app logs, crash reports, accessibility audits.
- Build Android internal APK/AAB via Play testing; iOS simulator build and TestFlight packaging after signing and App Store team access supplied. Do not claim App Store publication without it.
- Comply with Apple/Google requirements for financial applications, account deletion, privacy policy, affiliate claims and digital subscriptions; review appropriate in-app purchase requirements, avoid assuming direct external Stripe payment works for native digital features.
