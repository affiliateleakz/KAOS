# KAOS Trading Bot 1.2.2 — READABILITY + MINI VIEW FIX

Two user-reported problems in 1.2.1 are fixed: (1) once you entered Mini view
there was no way back to Mid or Max — the switcher lived in a sidebar that Mini
hides, and the title-bar Mini/Max buttons were hidden in mini mode; (2) many
fonts were far too small across all three views. No trading, strategy, bridge,
or AI logic changed.

## Mini view: always able to switch views (stuck-in-mini fixed)

- A Mini / Mid / Max switcher is now rendered inside BOTH title bars
  (`#kaos-page-title` and `#kaos-terminal-title`):
  `<div class="kaos-mini-viewmode">` with `.kaos-view-btn` buttons — the exact
  markup `popup.js` already wires, so no JavaScript changes were needed.
- It is hidden (`display:none`) in Mid and Max, where the sidebar switcher is
  visible; in Mini it appears in the title bar, left-aligned, while the close
  button stays at the right.
- Round-trip verified in the harness: Max → Mini (sidebar click) → Mid (title
  bar click) → Max, each click switching `body` classes and persisting
  `kaosViewMode` in localStorage exactly as before.
- The old rule that hid the title-bar Mini/Max buttons in mini mode
  (`body.kaos-mini .kaos-win-btn[data-win=min/max]{display:none}`) is now
  harmless to navigation: the new switcher is the mini view's way out, and the
  close button remains.

## Readability layer (v1.2.2) — bigger, user-friendly fonts everywhere

A last-loaded `<style id="kaos-readability">` layer bumps every previously
tiny font with `!important` so it wins all ties:

- Mini: toolbar labels 6.5→9px, inputs/selects 9.5→12px (26–28px tall),
  START/STOP 11→13px, stat values 14→16px, stat labels 6.5→8.5px,
  win buttons 26px with 13px glyphs.
- Mid: toolbar labels 9px, inputs 12px/32px, title 16px, stat values 16px,
  stat labels 9px, status strip 9.5px, trade-log entries 11px, nav buttons
  11.5px, VIEW MODE buttons 11px/30px tall (was 7.5px label / 9px buttons),
  nav brand 13px.
- Max: chart headers 9px, timeframe selects 8.5px, KPI values 11px,
  VIEW MODE buttons 11px/30px, terminal title 16px.

START/STOP font fix: the base `#start-btn` ID rule (`font:800 12px !important`)
outranked every class-based bump. The readability layer now also targets the
IDs (`body.kaos-mid #start-btn`, `body.kaos-mini #start-btn`,
`…#kaos-stop-btn`), which raises specificity above the ID rule — harness-verified
computed font-size is 13px in both Mini and Mid.

## Mini pill + menu: compact and non-overlapping

- The cloud status pill is compacted in Mini (9px font, tighter padding, the
  "POCKETOPTION · CONNECTED" segment hidden) and docks in the free title-bar
  strip between the new switcher (left) and the close button (right):
  measured [225,6,405,29] vs switcher ending at x=150 and close starting at
  x≈475 — no overlap.
- The pill's dropdown menu (Account / Switch Platform / Cloud Status / Sign Out)
  opens below the pill in mini mode instead of at the default bottom-left.

## Mini compaction: whole view fits the 200px popup band

With the larger fonts applied, mini was 214px tall (14px clipped at the 505×200
band). Compacted to fit with bigger text everywhere:

- workspace padding 6→4px and grid gap 6→4px; title bar 34→32px;
  toolbar padding 6→4px; inputs 28→26px; START/STOP 40→36px;
  stats row padding 6→3px, stat cards 38→34px.
- Harness result: body 505×184 (fits 505×200 with room to spare, zero clip),
  workspace clientHeight 184 == scrollHeight 184 (no internal scroll):
  title 32px + toolbar 49px + run rail 36px + stats 47px.

## Verified in headless-Chrome harness (stubbed chrome.* APIs)

- Mini 505×200: body 184px, no scroll, switcher visible with Mini active,
  fonts verified (labels 9px, inputs 12px, START 13px, stat values 16px),
  pill [225,6,405,29] clear of switcher and close button, zero errors.
- Mode switching: mini→max (title-bar button) sets `kaos-max`, max→mini
  (sidebar) sets `kaos-mini`, mini→mid (title-bar button) sets `kaos-mid`;
  localStorage `kaosViewMode` tracks each change.
- Mid 800×600: workspace 591px (no internal scroll), sidebar switcher
  (Mid active) fully visible, fonts verified; body scrollHeight 618 is only
  the 27px bottom padding reserved for the fixed pill — all content and the
  pill sit within the 600px viewport.
- Max 800×600: body 596px, no scroll, terminal title 40px, four 2×2 charts
  with 92px canvases, Strategy Builder panel, KPI strip, sidebar VIEW MODE
  buttons (11px) all visible; pill docked bottom-right in the status band.
- Zero runtime errors in all three modes; new markup is the only HTML change
  (two one-line insertions), no JS files touched.

## Packaging

- manifest.json bumped to 1.2.2 ("1.2.2 KAOS POPUP UI").
- Changed files vs 1.2.1: popup.html only (mini-viewmode markup + readability
  layer). Engine files unchanged: manifest metadata aside, popup.js,
  background.js, content.js, po-bridge.js, candidate7b_strategy.js,
  kaos-cloud*.js, kaos-banner-ui.css all keep their 1.2.1 behavior.

## Install (unpacked)

1. Download and unzip `KAOS_Trading_Bot_1.2.2.zip`.
2. Chrome → `chrome://extensions` → enable Developer mode.
3. "Load unpacked" → select the unzipped `KAOS_Trading_Bot_1.2.2` folder.
4. Click the KAOS icon in the Chrome toolbar — the bot opens as a popup.
   In Mini view, use the Mini / Mid / Max buttons in the title bar to switch
   views at any time; in Mid/Max the switcher is in the sidebar.
