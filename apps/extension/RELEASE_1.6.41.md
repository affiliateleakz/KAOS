# KAOS Trading Bot 1.6.41 — Pocket Option Chart Performance Fix

- Removed the full-page MutationObserver that reacted to every Pocket Option chart DOM/text/attribute mutation.
- Pocket Option AI shadow observation now polls only every 6 seconds while the tab is visible, plus an immediate probe when the AI control is clicked.
- Reduced expensive four-chart DOM discovery from every 1.2s to every 3s; sentiment scan runs every 6s.
- Deep visible-chart React/Vue history fallback now runs every 8s, only while visible, and automatically stops after four charts are captured or two minutes.
- OpenAI shadow heartbeat reduced from 1.5s to 3s; actual OpenAI calls remain decision-driven and rate limited.
- Trading WebSocket stream, candle processing, trade execution, KAOS Strategy, XGBoost/LightGBM learning, and OpenAI decision payload logic are unchanged.
