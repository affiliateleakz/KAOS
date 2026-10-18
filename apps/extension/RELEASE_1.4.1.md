# KAOS Trading Bot 1.4.1 — OFFLINE-RESILIENT

What you asked for: **"not working correctly"** — the recording (`error.mp4`)
shows the bot stuck on the **KAOS CLOUD · OFFLINE** gate with a RETRY-only
button, retrying for ~84 seconds and never reaching the dashboard. 1.4.1 fixes
that lockout: an unreachable cloud now surfaces as an honest **OFFLINE pill**
instead of a hard block on your local trading bot. The B32.24 PROFESSIONAL
CONSOLE shell from 1.4.0 is unchanged.

## What was wrong

`api.tradingwithkaos.com` sits behind a hosting anti-bot challenge layer
(LiteSpeed) that answers **every** request — including the extension's API
calls — with a `307` redirect to `https://recaptcha.cloud/…`. The extension's
`fetch()` follows the redirect, the cross-origin response is rejected, and the
startup check reports `OFFLINE`. The cloud UI then rendered a RETRY-only gate
that blocked the dashboard even though your local bot was fine. The server was
intermittently reachable (your recording shows login succeeding, then the
mid-flow re-check failing), which is why the failure looked random.

## What changed in 1.4.1

**1. The OFFLINE gate is no longer a dead end.**
- The OFFLINE panel now has a **CONTINUE OFFLINE** button (ghost style, next
  to RETRY CONNECTION). Clicking it proceeds to the dashboard with a red
  **KAOS CLOUD · OFFLINE** status pill — honest about the cloud state, never
  blocking the local bot.
- The choice is remembered for **12 hours** (`kaos_offline_ack` in
  `chrome.storage.local`): reopening the popup or reloading the page skips the
  gate while the cloud is unreachable, and goes straight to the OFFLINE pill.
  RETRY CONNECTION is still there whenever you want to re-check.
- Gate copy keeps the promise: *"Your local bot is unaffected; trade sync
  will resume automatically."*

**2. License enforcement is untouched.**
- SIGN IN, LICENSE INVALID and DEVICE NOT AUTHORIZED panels only render when
  the cloud **is** reachable, and they remain blocking. The offline escape
  cannot be used to bypass licensing — it only exists for the case where the
  cloud cannot be reached at all.

**3. No new capabilities, no logic moved.**
- This is a UX escape for an unreachable cloud plus a 12-hour preference
  flag. No trading logic, no broker integration, no strategy code was
  touched; the B32.24 shell and all controls behave exactly as in 1.4.0.

## Server-side fix (required on your end)

The extension-side escape keeps the bot usable, but cloud features (sign-in,
platform connect, trade sync) will stay flaky until the API is reachable:

- **Exclude `/api/*` from the LiteSpeed challenge layer** (or move the API
  behind the WAF entirely) so `api.tradingwithkaos.com` answers API traffic
  directly instead of 307-ing to `recaptcha.cloud`.
- A runtime host override (`KAOS_SET_HOST`) already exists in the extension
  if you need to point the cloud layer at a different API host while the
  challenge layer is being fixed.

## Verified in a headless-Chromium harness (v1.4.1 build)

- **Fresh gate**: with no ack stored, `KAOS_STARTUP → OFFLINE` renders the
  gate with **RETRY CONNECTION + CONTINUE OFFLINE**.
- **CONTINUE OFFLINE**: click → gate dismissed, red **KAOS CLOUD · OFFLINE**
  pill rendered, `kaos_offline_ack` persisted to storage.
- **Boot auto-skip**: reload with a fresh ack → gate skipped, OFFLINE pill
  rendered directly (no RETRY loop).
- **Ack expiry**: clearing the ack → gate returns.
- **License gate intact**: `BLOCKED / LICENSE_INVALID` still renders
  MANAGE MEMBERSHIP + RE-CHECK + SIGN OUT with **no** offline escape.
- Zero page errors, zero console errors in every state.

## Files changed vs 1.4.0

- `kaos-cloud-ui.js` — OFFLINE panel gains CONTINUE OFFLINE; new
  `ackOffline()` / `offlineAcked()` helpers; `boot()` skips the gate for 12h
  after an ack. (Header comment updated to v1.4.1.)
- `manifest.json` — `version: 1.4.1`, `version_name: "1.4.1 B32.24
  PROFESSIONAL CONSOLE · OFFLINE-RESILIENT"`, description string updated.
- `popup.html` / `popup.js` — version labels → 1.4.1.
- All other scripts/tools (`background.js`, `content.js`, `po-bridge.js`,
  `candidate7b_strategy.js`, `kaos-cloud.js`, `kaos-sync-client.js`,
  `kaos-learning-client.js`, CSS, icons) are unchanged from 1.4.0.

## Install / update

1. Download and unzip `KAOS_Trading_Bot_1.4.1.zip`.
2. Open `chrome://extensions`, enable **Developer mode**.
3. **Load unpacked** → select the unzipped `KAOS_Trading_Bot_1.4.1` folder
   (or click **Reload** on the existing KAOS entry after replacing the
   files).
4. If you still see the OFFLINE gate, click **CONTINUE OFFLINE** — the
   dashboard opens with the red OFFLINE pill, and the gate stays out of the
   way for 12 hours while the API challenge layer is being fixed.
