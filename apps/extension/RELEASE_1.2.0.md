# KAOS Trading Bot 1.2.0 — PROFESSIONAL BANNER UI

Full UI rebuild so the extension looks and behaves exactly like the official
KAOS Trading Bot hero banner (gold/charcoal professional theme), on the same
B32.24-continuation engine. No trading, strategy, bridge, or AI logic changed.

## CRITICAL FIX — popup.js rebuild

1.1.2x dev iterations left the dist `popup.js` with TWO concatenated copies of
the engine. At load time Chrome threw:

    SyntaxError: Identifier 'CSV_HEADERS' has already been declared

and the popup rendered dead/black. 1.2.0 rebuilds `popup.js` from the complete
pristine engine (single copy) plus exactly five reviewed UI patches and the
banner UI module appended once:

- `popup.js` is now 2,306 lines, single engine copy, parses clean (node --check).
- Every previously duplicated top-level declaration (CSV_HEADERS,
  DEBUG_CSV_HEADERS, SB_DEFAULT, kaosChartDiag, terminalTimer, terminalView,
  pineScripts, poEditingIndicator, ...) now exists exactly once.

## Banner-faithful popup UI

- Gold/charcoal banner theme applied last in `<head>` (`kaos-banner-ui` style
  block) so it wins over all legacy skins; popup.html footer reads 1.2.0.
- Header: KAOS logo mark, "KAOS TRADING BOT / TRADE WITH KAOS",
  "● POCKET OPTION: CONNECTED" status, window controls.
- Left sidebar: Dashboard · Trading · Strategy Builder · Charts · KAOS AI ·
  Performance · Settings, with VIEW MODE Mini / Mid / Max buttons.
- Toolbar: Market, Amount, Expiration, Strategy (Candidate 7B) + gear button —
  all wired to engine settings and persisted.
- Big green "▶ START KAOS" / red "■ STOP" buttons wired to the real start/stop
  flow (`setRunningUI` keeps button class + label in sync with engine state).
- Status strip: "Status: READY" · "Last Trade: WIN +$18.50" · "Balance: $…"
  driven by `updateStatsUI` from live `state.trades` / `state.sessionPnl`.
- SESSION STATS: Wins / Losses / Win Rate / P&L four-card grid.
- RECENT TRADES: Time / Market / Type / Result / P&L columns (`renderLog`
  5-column layout with win/loss coloring).
- Strategy Builder modal ("CHOOSE TRADING STRATEGY") opens from the toolbar
  Strategy box with all built-in/custom strategy cards.

## Mini / Mid / Max view modes

- Sidebar VIEW MODE buttons + title-bar window controls switch `kaos-mini`,
  `kaos-mid`, `kaos-max` body states; choice persists (localStorage
  `kaosViewMode`) and is restored on popup open.
- `alphaBotSetWindowMode` now sizes the real extension window per mode:
  Mini 505×640, Mid 940×680, Max/Charts maximized (1540×940 fallback).
- `route()` accepts `trading` and `settings` sidebar targets (in addition to
  dashboard/strategy) and exposes `window.kaosRoute` so the banner module and
  gear button can route programmatically; last view is remembered
  (`kaosLastView`).
- Mini mode collapses to the compact command bar; Max mode expands the full
  multi-chart terminal + Strategy Builder workspace.

## Packaging

- manifest.json bumped to 1.2.0 ("KAOS PROFESSIONAL BANNER UI"); description
  updated. Engine files unchanged: background.js, content.js, po-bridge.js,
  candidate7b_strategy.js, kaos-cloud*.js keep their 1.1.25 behavior
  (self-healing chart bridge retained).
- Verified in a headless-Chrome harness with stubbed chrome.* APIs: zero
  runtime errors; all views, view modes, toolbar controls, start/stop flow,
  stats strip, and trades table render and respond correctly.

## Install (unpacked)

1. Download and unzip `KAOS_Trading_Bot_1.2.0.zip`.
2. Chrome → `chrome://extensions` → enable Developer mode.
3. "Load unpacked" → select the unzipped `KAOS_Trading_Bot_1.2.0` folder.
4. Open Pocket Option, log in, click the KAOS icon, and trade with KAOS.