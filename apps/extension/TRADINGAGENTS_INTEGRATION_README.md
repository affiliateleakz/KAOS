# KAOS 1.6.56 + TradingAgents Research Lab

This is the user's **KAOS Trading Bot 1.6.56 SPECIALIST RESEARCH** release, augmented with a **separate research-only TradingAgents lab**. The original popup.js, content.js, background.js, PO bridge, AI learning, authentication, and trade execution logic are unchanged.

## Install
1. Extract the ZIP, then in Chrome extensions enable Developer Mode and **Load unpacked** using the folder containing `manifest.json`. Back up the original extension first.
2. Open the KAOS bot and click **TradingAgents Lab ↗** in the sidebar. The lab opens in its own Chrome tab.
3. Install the official Python TradingAgents library (https://github.com/TauricResearch/TradingAgents) and configure its data/LLM provider credentials as directed by that project. The library is not included.
4. Run `python research_service/server.py` on the same computer. It listens on 127.0.0.1:8765.
5. In the lab click **Check server**, then enter a stock ticker supported by TradingAgents (e.g. AAPL), date and click **Run multi-agent research**.

## Limitations
- The service supports **research only**; no broker order placement or automatic live strategy veto/approval.
- Pocket Option OTC symbols, 5-second candles and short expiry trades are **not natively supported** by TradingAgents.
- The TradingAgents library and its model/data providers are separate installations and may have costs.
- Source and JS syntax checked; live TradingAgents/Pocket Option integration not verified.
- All existing KAOS membership/login functionality is preserved at source level, not revalidated against a live server.
