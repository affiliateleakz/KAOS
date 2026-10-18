# KAOS Trading Mobile — Android + iOS development foundation

This is an **Expo / React Native source project**, not an APK or an App Store-ready iOS binary. It connects to the existing KAOS 3.0 Opportunity Radar research API (`GET /api/v1/intelligence/opportunities`, `GET /api/v1/intelligence/status`). It does not alter or replace the trading bot, website, or backend. No live trades or live data are fabricated.

## Run
1. Install Node.js LTS and npm.
2. `npm install`
3. Copy `.env.example` to `.env` and set the real KAOS API base URL.
4. `npx expo start` and open in Expo Go (device compatibility permitting), or use an Expo development build.
5. For signed production apps, configure Expo EAS Build, developer accounts, production authentication and privacy disclosures.

## Current functionality
- Android/iOS navigation and dark KAOS design
- Authenticated read-only opportunity feed with market category filters
- Research evidence details, timestamps and links to original sources
- Refresh, empty states, membership/expired-session error handling
- Access token stored in OS-backed SecureStore, sign out removes it

## Critical before production
- **Authentication:** Current dev sign-in takes an already issued KAOS access token for testing only. Replace with OAuth 2.0 Authorization Code + PKCE and system browser / app deep link, and implement secure server-side refresh-token rotation. Never ask end users to paste tokens. KAOS backend presently issues short-lived JWTs and cookie refresh tokens; a mobile token-exchange endpoint must be designed, audited and implemented. Do not embed Google client secrets or broker keys in the app.
- **Push alerts:** Not implemented; needs device token registration, authenticated preferences, server-side notification jobs, delivery provider and opt-in permissions.
- **Other screens:** Charts, screeners, Follow the Money, news, social, portfolio, broker positions, AI chat, and execution are planned but not implemented.
- **Backend:** Must be deployed with CORS/network security and entitlement enforcement, HTTPS and actual collectors. Existing opportunity API reports `live_feeds_included: false` and will show no results until ingestion.
- **Security:** Add device session management, rate limiting, threat monitoring, accessibility, app-store privacy requirements, and security testing.
- **Live trading:** Deliberately disabled. Broker-specific mobile execution must be independently validated and authorized.

## New in mobile 0.2 development iteration
- Watchlist: save and remove opportunity assets with device-local encrypted SecureStore storage; reopen items that have recent ingested research.
- Account and Alerts preferences: user-selectable alert categories, with clear notice that push registration and delivery are not implemented.
- Navigation to Watchlist and Settings from the radar, and Save action from opportunity research details.
- Device watchlists and alert preferences are **not yet synced** with the KAOS cloud or other devices.

## Validation performed
- ZIP archive integrity checked.
- Backend opportunity endpoint paths verified against KAOS 3.0 development backend.
- React Native dependency installation, TypeScript compilation, Android/iOS native builds, device testing and production API integration were **not** completed in this environment.
