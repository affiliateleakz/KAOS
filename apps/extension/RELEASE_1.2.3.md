# KAOS Trading Bot 1.2.3 — TRUE FULL-SCREEN MAX VIEW

Reported problem: **"max view is not doing full screen."** Correct — a Chrome
extension toolbar popup is hard-capped at **800 × 600 CSS px**, so the inline
"Max" layout could only ever fill that small popup, never the screen. 1.2.3
makes Max genuinely full screen.

## What changed

### 1. Max now opens a real, full-viewport tab
- Pressing any **Max** control — the title-bar `□` button (`#kaos-win-max`,
  `#kaos-win-max2`, tooltip "Max view (opens full screen)") or the sidebar
  **VIEW MODE → Max** button — calls `kaosEnterMax()`.
- Inside the installed extension (`chrome-extension://`) it opens
  `popup.html?kaosFull=1` in a new active browser tab via
  `chrome.tabs.create` + `chrome.runtime.getURL`, then closes the little
  popup. `tabs` permission was already present in the manifest.
- In that tab `initViewMode()` detects `kaosFull=1`, adds `body.kaos-fullpage`
  and locks the view to Max — every 800 × 600 cap is lifted and the 4-chart
  terminal uses the whole window at any monitor size.
- If the tab cannot be opened (e.g. running the page over `http://`, or a
  blocked tab), `kaosEnterMax()` silently **falls back to the inline Max
  layout** — nothing breaks, the user still gets the charts terminal.

### 2. New ⛶ Full-screen toggle
- Added a `⛶` button to **both** title bars (next to Min / Max / Close):
  `#kaos-fs-btn-main` (dashboard bar) and `#kaos-fs-btn` (terminal bar),
  wired through `kaosToggleFullscreen()` to the browser Fullscreen API
  (`requestFullscreen` / `exitFullscreen`), so you can hide even the browser
  chrome and use the charts on the full display.

### 3. Full-page layout rebuilt (root cause of the earlier overflow)
- `#terminal-live` is a 2-column grid, but only `.four-grid` (`grid`) and
  `.sb-wrap` (`sb`) had named areas. The KPI strip, the chart toolbar and the
  note were **auto-placed into extra implicit rows**, which pushed the chart
  toolbar off the bottom of the viewport.
- 1.2.3 gives **every** child an explicit area and a flexible track:

  ```
  #terminal-live{grid-template-columns:minmax(0,1fr) 340px;
                 grid-template-rows:minmax(0,1fr) auto;
                 grid-template-areas:"grid sb" "kpis selbar";}
  ```
  Row 1 (chart board + strategy builder) absorbs all free height; row 2 holds
  the KPI strip + chart toolbar. Charts flex-shrink (`min-height:0`) instead of
  using rigid `calc()` heights, so nothing overflows at any resolution.

## Verified in a headless-Chromium harness
Measured element boxes (all inside the viewport, page scrollHeight == viewport,
`errs:0`) and screenshots captured:

| Viewport | terminal-live bottom | 4-chart grid bottom | chart toolbar | strategy builder |
|----------|----------------------|---------------------|---------------|------------------|
| 1600×900 | 892 (≤ 900)          | 816                 | 832–884       | 55–816           |
| 1920×1080| 1072 (≤ 1080)        | 996                 | 1012–1064     | 55–996           |

Regression-checked the inline popup modes at **800 × 600** (no viewport
overflow, no JS errors):
- **Mini** — `kaos-mini`, mini view switcher present, view fits (h ≈ 184).
- **Mid** — `kaos-mid`, workspace fills the popup.
- **Max (fallback)** — `kaos-max`, 4-chart terminal + chart toolbar all inside
  the popup (`terminalLive` bottom 561 ≤ 600, toolbar 491–553).

Screenshots: `shot_fullpage_v123.png` (1600×900). Older `shot_mini_v9.png`,
`shot_mid_v9.png`, `shot_max_v9.png` still show the popup modes.

## Files changed vs 1.2.2
- `popup.html` — full-page CSS block (explicit grid areas), ⛶ buttons in both
  title bars, version labels → 1.2.3.
- `popup.js` — `kaosFullPage()`, `kaosCanOpenTab()`, `kaosEnterMax()`,
  `kaosToggleFullscreen()`, `setViewMode(mode,persist)`, full-page-aware
  `initViewMode()`, and `[data-win]` wiring.
- `manifest.json` — version `1.2.3`, name `1.2.3 KAOS FULL-SCREEN MAX`,
  description updated.
- All other scripts/tools (`background.js`, `content.js`, `po-bridge.js`,
  `kaos-cloud*.js`, `kaos-banner-ui.css`, `kaos-home-ui*.css`) are unchanged
  from 1.2.2.

## Install / update
1. Download and unzip `KAOS_Trading_Bot_1.2.3.zip`.
2. Open `chrome://extensions`, enable **Developer mode**.
3. **Load unpacked** → select the unzipped `KAOS_Trading_Bot_1.2.3` folder
   (or click **Reload** on the existing KAOS entry after replacing the files).
4. Click the KAOS toolbar icon → **Max** (the `□` button or sidebar Max) opens
   the full-screen charts tab. Use **⛶** to hide the browser chrome entirely.
