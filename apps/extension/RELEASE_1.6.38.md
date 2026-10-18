# KAOS Trading Bot 1.6.38 — OpenAI Brain Live Shadow

- Built directly from the user-provided 1.6.37 build.
- OpenAI Brain now actually calls the authenticated KAOS `/api/v1/ai/brain` endpoint.
- Calls are made from the extension background context using the existing KaosCloud auth/session/device headers.
- Compact live market snapshots are sent after fresh KAOS decisions, rate-limited to at most one request per 10 seconds.
- UI now reports real states: CONNECTED, AUTH REQUIRED, MEMBERSHIP REQUIRED, SERVER NOT CONFIGURED, OFFLINE, SERVER ERROR, REQUEST ERROR, or WAITING FOR MARKET.
- Successful OpenAI output remains SHADOW/LEARNING ONLY and cannot place or veto trades.
- No OpenAI API key is stored in the extension.
