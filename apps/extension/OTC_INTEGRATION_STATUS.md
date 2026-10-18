# KAOS OTC research bridge status

Added: `POST /otc/analyze` to the existing local Python service. Accepts 60–12,000 closed OHLC candles and returns three deterministic technical-agent votes and a research-only BUY/SELL/HOLD assessment. Added CSV import to the existing TradingAgents Lab. The stock TradingAgents workflow is retained.

**Not complete:** No live Pocket Option OTC market feed wired into this research endpoint, no validated AI prediction, no trade execution linkage, no verification of production membership/auth/cloud/PO connectivity, no actual TradingAgents LLM support for OTC symbols. Do not use research votes to authorize trades.

Start with `python research_service/server.py`; open TradingAgents Lab and upload a CSV containing `open,high,low,close`. Closed candles only, sorted oldest to newest.
