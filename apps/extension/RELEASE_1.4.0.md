# KAOS Trading Bot 1.4.0 — B32.24 PROFESSIONAL CONSOLE

What you asked for: **"I want this bot to look just like the samples in this
image and function correctly … I want it to look exactly like the second
picture"** (the B32.24 professional UI preview: gold/black shell, navy
stat cards, warm-black mini console). 1.4.0 rebuilds the whole shell around
the B32.24 reference screenshots — header, sidebar, dashboard cards, footer
strip — and rebuilds **Mini view as the flat reference console**, while every
real control keeps working (B32.24 logic untouched).

## What's new vs 1.3.0

**1. B32.24 shell (all view modes).**
- New header: gold KAOS brand block, live **status pills** wired to real bot
  state (Pocket Option / Server / Data Feed / Bot Status / AI Learning),
  session popover, ID + version badge, window controls.
- Gold/black sidebar with artwork block and view-mode buttons
  (Mini / Mid / Max).
- Footer strip on every page: `KAOS TRADING BOT v1.4.0`, feature blurbs
  (Automated Execution / AI Learning Engine / Multi-Market Ready / Advanced
  Risk Management), live date-time clock, Support button.
- `popup.js` gains a small appended v1.4.0 runtime module (~140 lines) that
  mirrors existing bot state into the pills, session popover, bottom status
  cards, nav badges and the footer clock — **read-only mirrors, no new
  capabilities, no logic moved**.

**2. Mini = the B32.24 reference console (exact match).**
Mini (505 px) is now a flat professional console matching `ui_mini.png`:
- Full-bleed warm-black title strip (36 px, `#0d0c08→#090906`) with brand,
  view buttons and window controls.
- One row, four equal **borderless dark fields** (`#0d0d0b`, labels
  `#c9d4dc`, 7.5 px mono caps): MARKET / AMOUNT / EXPIRATION / STRATEGY.
- 50/50 run rail: **START KAOS** bright green gradient (`#1bce5b→#15b350`,
  dark text), **STOP** dark maroon `#4c131a` with dim `#5c5e61` text.
- Four **navy stat cards** (`#091520`, steel-blue border `#1d5f86`, label
  above value): Wins / Losses / Win Rate / P&L — wins/rate/P&L in
  `#1fe05f`, losses in `#ef3541`, real live values.
- Everything not in the reference mini is hidden: sidebar nav, live chart,
  floating pills, footer strip, card headers, toolbar gear. Canvas
  `#04080c`.
- New CSS layer `16e. MINI = B32.24 reference console` in `popup.html`
  (specificity-matched against the k13/kb legacy rules so nothing fights).

**3. Fullpage / Mid / Max re-verified.**
- Fullpage dashboard (sidebar + control center + right rail + four bottom
  cards + footer strip) renders correctly; the previously reported "ghost
  band" between the bottom cards and the footer was investigated with
  live-DOM probes: the area is **plain empty workspace background — the
  footer strip renders exactly once** (`elementFromPoint` at the band hits
  `kaos-app-workspace`; footer occupies y≈990–1024 of 1024 and appears once
  in the DOM). Footer-strip vertical placement is intentionally approximate.
- Mid mode unchanged from the verified v14 build (sidebar, header pills,
  control center, right cards, bottom cards).

## Verified in a headless-Chromium harness (v1.4.0 build)

- **Mini 600×800** vs `ui_mini.png`: one-row toolbar (4 equal 117 px fields,
  `min-width:0` beats the legacy `min-width:120px` rule), 36 px full-bleed
  title strip (`margin:-8px -8px 8px`), 50/50 rail (241 px/241 px),
  nav/chart/footer/pills/card-head/gear all `display:none`, stat cards
  `column-reverse` with sampled colors above. Screenshot
  `_v14_mini_600x800.png`.
- **Fullpage 1536×1024** (`?kaosFull=1`): dashboard after
  `terminalHide()` matches the B32.24 layout; ghost-band probes as above.
  Screenshot `_v14_fullpage_dash_check.png`.
- **Mid 600×800**: unchanged, screenshot `_v14_mid_600x800.png`.
- Controls exercised in-browser: Mini→Mid→Max switching, amount input
  accepts edits, START enabled / STOP correctly disabled while idle, nav
  click routes. **Zero page errors, zero console errors** in every state.

## Files changed vs 1.3.0

- `popup.html` — k14 header + screen-main rebuild, k14 style layer, new
  16e mini-console section, version labels → 1.4.0.
- `popup.js` — appended v1.4.0 runtime module (pills / session popover /
  nav items / bottom cards / footer clock mirrors).
- `manifest.json` — `version: 1.4.0`, `version_name: "1.4.0 B32.24
  PROFESSIONAL CONSOLE"`.
- All other scripts/tools (`background.js`, `content.js`, `po-bridge.js`,
  `candidate7b_strategy.js`, `kaos-cloud*`, `kaos-banner-ui.css`,
  `kaos-home-ui*.css`, icons) are unchanged from 1.3.0.

## Install / update

1. Download and unzip `KAOS_Trading_Bot_1.4.0.zip`.
2. Open `chrome://extensions`, enable **Developer mode**.
3. **Load unpacked** → select the unzipped `KAOS_Trading_Bot_1.4.0` folder
   (or click **Reload** on the existing KAOS entry after replacing the
   files).
4. Click the KAOS toolbar icon → pick **Mini** in the title bar for the
   B32.24 console, **Mid/Max** for the full shell; **⛶** toggles browser
   chrome, `?kaosFull=1` boots the full-page terminal.
