# KAOS Trading Bot 1.2.1 — REAL TOOLBAR POPUP UI

The extension now opens as a genuine Chrome toolbar popup (the small window
under the KAOS toolbar icon), exactly like the official KAOS Trading Bot
hero banner. 1.2.0 opened a separate floating app-style window; 1.2.1 removes
that and makes the banner UI live inside `action.default_popup`. No trading,
strategy, bridge, or AI logic changed.

## Toolbar popup conversion

- `manifest.json` adds `"action.default_popup": "popup.html"` (MV3) — clicking
  the toolbar icon now opens the banner UI as a real popup instead of a
  background page/floating window.
- Removed the floating-window opener from `background.js` / `popup.js`
  (the "app within an app" window from 1.2.0 is gone).
- `popup.js` view-mode and close logic made popup-safe: no
  `chrome.windows`/`window.resizeTo`/`window.open` sizing calls; Mini/Mid/Max
  only switch body-state classes and persist the choice
  (localStorage `kaosViewMode`, restored on popup open).

## Banner CSS rebuilt to popup dimensions

- Mini ≈ 505px compact command bar; Mid/Max fit the standard ≤ 800×600 popup
  envelope (popup opens at 800×600; body renders 800×596 + 27px status band).
- Header, sidebar, toolbar, stats strip, trades table, strategy builder and
  pill re-anchored for popup coordinates (cloud pill docked in the status
  band under the footer; in mini it docks in the title-bar strip, left of the
  close button).

## Max (charts terminal) fixes

- Double-screen stacking bug fixed at the root: four separate style blocks had
  `#screen-main.kaos-five-app.active,#screen-chart.kaos-five-app.active{display:flex!important}`,
  whose `!important` beat the inline `display:none` set by `terminalShow()`.
  `!important` removed from ALL occurrences so inline display styles win again;
  `#screen-main` hides and `#screen-chart` [0,0,800,569] shows correctly.
- Max-mode vertical overflow (body was 1456px scroll) fixed by the
  "KAOS POPUP FIT" compaction layer: `#terminal-workspace` capped at 573px with
  no scroll (tws scrollHeight 569 = clientHeight 569), four-grid charts
  compacted to 2×2 (390px), KPI strip 30px, Strategy Builder capped at 424px
  with its own internal scroll, selectbar compacted.
- Chart-selectbar clipping fixed: content now ends 10px above the workspace
  clip edge (buttons bottom y=551 vs clip edge y=561); the real culprit was
  base `min-height:34px` overriding `height:20px!important` — compaction now
  also sets `min-height:0!important` on the strategy select and toolbar
  buttons. Selectbar scrollHeight 60 ≤ 62 cap, fully visible.
- Accepted trade-offs in Max: `mc-strategy-truth` ellipsized to one line,
  `mc-indicators` row hidden; `#terminal-live` residual 0px (scrollHeight ==
  clientHeight after the selectbar fix).

## Verified in headless-Chrome harness (stubbed chrome.* APIs)

- Max 800×600: body 596px, no body scroll, `#screen-main` display:none,
  `#screen-chart` [0,0,800,569], tws 569/569 (no scroll), terminal-live
  508/508 (no scroll), selectbar fully visible, pill in the clear 27px
  status band (no footer overlap).
- Mid 800×600: dashboard [0,0,800,573], pill [417,569,792,596] in status band.
- Mini 500×500: banner 505×200 command bar, pill docked in title bar.
- Zero runtime errors in all three modes; `popup.js` and `background.js`
  parse clean (`node --check`).

## Packaging

- manifest.json bumped to 1.2.1 ("KAOS POPUP UI"); description updated.
- Changed files vs 1.2.0: manifest.json, popup.html, popup.js,
  background.js, kaos-banner-ui.css. Engine files unchanged: content.js,
  po-bridge.js, candidate7b_strategy.js, kaos-cloud*.js keep their 1.1.25
  behavior (self-healing chart bridge retained).

## Install (unpacked)

1. Download and unzip `KAOS_Trading_Bot_1.2.1.zip`.
2. Chrome → `chrome://extensions` → enable Developer mode.
3. "Load unpacked" → select the unzipped `KAOS_Trading_Bot_1.2.1` folder.
4. Click the KAOS icon in the Chrome toolbar — the bot opens as a popup.
   Use Mini / Mid / Max in the sidebar to switch view modes.
