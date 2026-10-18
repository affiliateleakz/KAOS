# KAOS 1.6.5 — Server OFFLINE deep scan

## Root cause found in extension
The header's `Server` pill did **not** test the server. It called `KAOS_STARTUP`, which is a
full authenticated startup workflow. Any network failure while restoring `/extension/me`
or registering `/devices/register` was converted into `OFFLINE`, so the UI displayed
`Server OFFLINE` even when the public KAOS API health endpoint was online.

That conflicts with the already-confirmed public `/api` response.

## Fix
- Added `KaosCloud.health()` which independently probes `https://api.tradingwithkaos.com/api`
  (and `/api/` fallback).
- Added `KAOS_HEALTH` service-worker message.
- Header Server pill now uses only the public health check.
- Auth/session failures no longer masquerade as server outages when health succeeds.
- If health succeeds but authenticated extension endpoints fail, the UI reports an
  account/session connection error and asks for sign-in instead of `SERVER OFFLINE`.
- JWT parsing accepts both camelCase (`accessToken`, `refreshToken`) and common snake_case
  (`access_token`, `refresh_token`) server responses.
- Pocket Option connectivity remains completely independent.

All JS syntax checks passed.
