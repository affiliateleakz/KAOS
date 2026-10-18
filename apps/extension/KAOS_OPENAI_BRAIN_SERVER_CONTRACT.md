# KAOS OpenAI Brain server contract

Extension endpoint: `POST /api/v1/ai/brain`

Requirements:
1. Authenticate the KAOS user.
2. Require an ACTIVE paid membership/license before inference.
3. Keep `OPENAI_API_KEY` server-side only.
4. Call the current OpenAI Responses API.
5. Request a strict structured result:
   - `direction`: BUY | SELL | HOLD
   - `confidence`: 0..100
   - `expirySec`: 5 | 10 | 15 | 30 | null
   - `regime`: string
   - `setupType`: string
6. Return only the structured result to the extension.
7. Log the prediction ID and later 5s/10s/15s/30s outcomes for validation.
8. Initial mode is SHADOW. Do not execute or veto trades from OpenAI output.

Recommended inputs are compact numeric/enum snapshots, not screenshots:
asset, current price, 5s/15s/30s/60s OHLC-derived structure, volatility,
EMA/RSI/MACD/BB/ZigZag state, KAOS Strategy proposal, XGBoost probability,
LightGBM probability, Pocket Option AI observation, external signal observation.
