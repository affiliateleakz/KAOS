# KAOS Trading Bot 1.6.42

## KAOS Strategy SR1.0
- Renames the signature live strategy to **KAOS Strategy**.
- 30s support/resistance levels with 60s trend context.
- Four deterministic sleeves: S/R rejection, failed breakout + reclaim, breakout + retest, and S/R trend continuation.
- 5s/15s confirmation entries.
- Adaptive expiries: 15s continuation, 20s rejection/reclaim, 25s breakout-retest.
- BUY and SELL are symmetric.
- OpenAI/XGBoost/LightGBM remain learning/shadow context only and do not veto or create KAOS Strategy trades.
- Retains 1.6.41 Pocket Option performance throttling and 1.6.40/1.6.39 fixes.
