# KAOS Trading Bot 1.6.39

- Fixed Dashboard strategy catalog: strategy cards are now actionable instead of display-only.
- Added one canonical per-chart strategy setter so Dashboard cards, Dashboard chart dropdowns, and Charts-tab dropdowns update the same `terminalSlotProfiles` state.
- Strategy changes persist to Chrome local storage and immediately refresh the selected chart UI.
- Dashboard strategy catalog now highlights the strategy assigned to the active chart.
- Existing OpenAI Brain live-shadow integration from 1.6.38 retained.
