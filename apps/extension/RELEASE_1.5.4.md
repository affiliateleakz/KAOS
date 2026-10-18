# KAOS Trading Bot 1.5.4 — Cloud UI Scope Fix

Root cause of the screen appearing when Pocket Option reloads:
`kaos-cloud-ui.js` and `kaos-cloud-ui.css` were listed as Pocket Option content scripts in
manifest.json. Therefore every Pocket Option reload injected the KAOS login/offline overlay
directly into the broker page.

1.5.4 removes the cloud UI JS/CSS from all Pocket Option content-script declarations.
The cloud UI remains loaded by popup.html, where it belongs.

Also repairs stale saved API-host values that point at the public website instead of
`https://api.tradingwithkaos.com`.

Trading content scripts, Candidate 7B, Pocket Option bridge and chart code remain injected.
All JavaScript passes syntax validation.
