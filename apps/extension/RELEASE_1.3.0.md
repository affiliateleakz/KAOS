# KAOS Trading Bot 1.3.0 — APP-SHELL UI · SEVEN DISTINCT PAGES

What you asked for: **"I want the look/UX to be completely different: the
Dashboard tab duplicates the Trading tab, Charts and AI are almost merged;
make an App-style UI."** 1.3.0 replaces the single long scrolling popup with
a real application shell — a fixed gold-on-dark **sidebar** plus **seven
distinct pages**, each with its own content, while every trade-control keeps
its original IDs and behaviour (B32.24 logic untouched).

## The new information architecture

Sidebar (identical in both shells, sections as real group headers):

```
KAOS TRADING            ← brand block
TRADING
  ▤ Dashboard           ← live market + Start/Stop (was: top of old popup)
  ⨇ Trading             ← control centre / strategy builder + trade panel
  ▟ Charts              ← multi-chart terminal (real chart shell)
INTELLIGENCE
  ≋ Advanced            ← live diagnostics + AI learning lab
  ✦ KAOS AI             ← AI model status / learning lab (terminal page)
  ◐ Performance         ← results, stats, trade history (terminal page)
────
  ⚙ Settings            ← appearance / data / support / about
VIEW MODE  Mini Mid Max ← stays in the sidebar, always reachable
```

- **Dashboard** — Live Market panel (mirrors the real Chart-1 canvas),
  Candidate 7B chips, market / amount / expiry / strategy, START KAOS / STOP,
  status + balance strip. The old duplicated trading blocks are **not**
  repeated here any more.
- **Trading** — KAOS Control Centre: strategy choice, data import, backups,
  exports, trade amount and trading mode. Distinct content, full width.
- **Charts / KAOS AI / Performance** — these open the **chart (terminal)
  shell** and switch its three terminal pages (`terminal-live`,
  `terminal-ai`, `terminal-analytics`); the sidebar highlights the active
  page in that shell too, so Charts and AI are clearly separated at last.
- **Advanced** — Live diagnostics + AI Learning Lab (the old "strategy"
  builder view is aliased here, so old `route('strategy')` calls still work).
- **Settings** — new dedicated page with four cards: **App appearance**
  (Mini / Mid / Max / Full screen), **Data & backup** (import / backup /
  diagnostics — wired to the existing controls), **Support** (contact
  button), **About KAOS** (VERSION 1.3.0 · BUILD KAOS APP SHELL · ENGINE
  Candidate 7B).

## How it is built (presentation only — no logic moved)

- New top CSS layer `<style id="kaos-app-v13">` in `popup.html`: app shell,
  sidebar, page title bar, dashboard cards, trading/advanced/settings pages,
  chart-shell polish, mini layout and responsive rules.
- Pages are **view classes** on `#screen-main`
  (`view-dashboard / view-trading / view-advanced / view-settings`); CSS
  shows/hides the right regions per view and view mode. No DOM is moved at
  runtime, so all existing bindings survive.
- `popup.js` gains a small `kaosFivePageUI` block: `route(view)` dispatches
  main-shell views vs terminal pages, `setMainView()` applies the view class
  *after* `showScreen('main')` (which force-adds `view-dashboard`),
  `setTerminalPage()` switches the three terminal pages and its workspace
  title. Nav buttons are bound via `data-kaos-view`; Settings-page buttons
  reuse the original import/export/diagnostic/support controls; the
  dashboard canvas keeps mirroring the real chart canvas (900 ms).
- Opening the popup still lands on **Dashboard**; `?kaosFull=1` still boots
  the full-page Max terminal (1.2.3 behaviour unchanged, incl. the ⛶
  Fullscreen-API toggle in both title bars).

## Verified in a headless-Chromium harness (v1.3.0 build)

Full routing matrix — **7 pages × Mini/Mid/Max = 21 states** plus **7 pages
in the full-page tab (`?kaosFull=1`)**: every state checked
`window.__kaos_errs` (**0 errors everywhere**), active shell, view class,
terminal page id, active sidebar item and visibility of the page's key
region. 28 screenshots captured (`shots_k13/`):
`mini|mid|max|fullpage × dashboard|trading|charts|advanced|ai|performance|settings`.

Spot-checked visually: sidebar sections render, Dashboard shows the live
candle chart (real mirrored canvas), Trading/Advanced/Settings are distinct
pages, About card reads **VERSION 1.3.0**, footer reads `KAOS TRADING BOT · 1.3.0`.

Also re-verified: `node --check popup.js` and `python3 -m json.tool
manifest.json` pass.

## Files changed vs 1.2.3

- `popup.html` — app-shell markup (sidebars in both shells, page title bar,
  settings page), `kaos-app-v13` CSS layer, version labels → 1.3.0.
- `popup.js` — `kaosFivePageUI` routing block (route / setMainView /
  setTerminalPage / showKaosScreen), nav + settings bindings, dashboard
  canvas mirror, startup route.
- `manifest.json` — `version: 1.3.0`, `version_name: "1.3.0 KAOS APP
  SHELL"`, description updated.
- All other scripts/tools (`background.js`, `content.js`, `po-bridge.js`,
  `candidate7b_strategy.js`, `kaos-cloud*`, `kaos-banner-ui.css`,
  `kaos-home-ui*.css`, icons) are unchanged from 1.2.3.

## Install / update

1. Download and unzip `KAOS_Trading_Bot_1.3.0.zip`.
2. Open `chrome://extensions`, enable **Developer mode**.
3. **Load unpacked** → select the unzipped `KAOS_Trading_Bot_1.3.0` folder
   (or click **Reload** on the existing KAOS entry after replacing the files).
4. Click the KAOS toolbar icon → the sidebar takes you to any page; **Max**
   opens the full-screen tab; **⛶** hides the browser chrome.
