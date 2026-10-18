# KAOS Trading Bot 1.4.4 — APP WINDOW FIT

Fixes the collapsed/sliver window from 1.4.3.

- Removes Chrome toolbar `default_popup`; the toolbar icon now opens KAOS as a real standalone popup application window.
- MID opens at 1280×860.
- MINI resizes the actual app window to 520×720.
- MAX resizes the actual app window to 1500×940 (Chrome/Windows may clamp to the available desktop).
- The HTML now fills 100% of the app viewport instead of forcing a body wider than Chrome's toolbar-popup surface.
- Keeps the 1.4.3 restored cloud client.
- Does not change B32.24 trading, Pocket Option bridge, candles, or strategy logic.
