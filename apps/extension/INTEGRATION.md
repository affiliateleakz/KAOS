# KAOS extension — cloud integration (INTEGRATED)

The KAOS cloud clients are **already integrated into the real bot** in this directory. This file is a
quick map; the full contract is in `../EXTENSION_API.md` and the strategy in `../STRATEGY_ENGINE.md`.

## What's wired
- `background.js` (MV3 service worker) `importScripts('kaos-sync-client.js','kaos-learning-client.js',
  'kaos-cloud.js')` and hosts the `KAOS_*` message router + alarms-based sync flush + `kaosOnTradeEvent`.
- `kaos-cloud.js` (`self.KaosCloud`) — auth/session/refresh/logout, membership+entitlement
  (`/extension/me`), device register/authorization, `/bot/config`, `/bot/release`, `/platforms`,
  `/ai/predict`, `/ai/consent`, and the full `startup()` orchestration.
- `kaos-cloud-ui.js` + `.css` — startup/auth/platform overlay and the compact post-connect status
  pill; injected on Pocket Option pages and inside the popup window.
- `kaos-sync-client.js` — durable, idempotent trade-event queue → `POST /api/v1/trading/events`.
- `kaos-learning-client.js` — consent-gated 104-feature learning samples → `POST /api/v1/ai/learning-samples`.

## Emitting trade events from the bot
From `content.js` (or the popup), send to the worker:
```js
chrome.runtime.sendMessage({ type: 'KAOS_TRADE_EVENT', eventType: 'BROKER_CONFIRMED',
  trade: { tradeId, signalId, platform:'pocket_option', asset, direction, strategy:'KAOS_BERSERKER',
           strategyVersion:'C9.0', timeframe:'5s', expiration:'45s', entryPrice, brokerOrderId } });
// on settlement (adds a learning sample when consent is ON):
chrome.runtime.sendMessage({ type: 'KAOS_TRADE_EVENT', eventType: 'TRADE_RESULT',
  trade: { tradeId, outcome:'WIN', settlementPrice, featureVector /* number[104] */ } });
```
`eventId` defaults to `"<tradeId>:<type>"` → the server dedupes; a cloud outage never re-submits a
broker order, it only queues & replays the sync event.

## Configure the KAOS host
`chrome.runtime.sendMessage({ type:'KAOS_SET_HOST', host:'https://your-kaos-host' })` (persisted).
Add the host to `manifest.json` `host_permissions`.

## Tests
- `node kaos_integration_test.cjs` (set `KAOS_HOST`) — live login→license→device→platform→sync
  (idempotent dedupe)→learning (consent on/off). 13/13.
- `node test_sync_client.cjs` — offline queue, recovery drain, idempotency, 401-refresh, 4xx drop.
