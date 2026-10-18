# KAOS Trading Bot 1.5.0 — Deep UI Cleanup

A structural pass over the accumulated 1.4.x interface.

- Unified the Charts sidebar with the main KAOS navigation.
- Removed obsolete Trading and Advanced navigation from the customer UI.
- Legacy Trading routes now go to Dashboard.
- Legacy Advanced routes now go to Build Strategy.
- Build Strategy displays the one real `#strategy-builder` as its own page.
- Charts cannot render the Strategy Builder.
- Rebuilt `#terminal-live` as a vertical page: KPI strip, chart toolbar, full-width 2×2 chart grid, note.
- Removed the old two-column `grid / sb` layout behavior that pushed charts to the side.
- AI and Performance remain independent terminal pages.
- Added authoritative overflow/min-width rules to stop old fixed-size CSS from overlapping/clipping pages.
- Preserved B32.24 trading, Pocket Option bridge, chart renderer, strategies and 1.2 cloud client.

Validation:
- one `#strategy-builder`
- builder physically outside `#screen-chart`
- one `#terminal-live`
- one `#terminal-four-grid`
- no Trading/Advanced buttons in Charts navigation
- all JavaScript files pass syntax validation
