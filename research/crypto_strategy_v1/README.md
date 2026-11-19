# KAOS Micro Reversion Research v1

**A strategy and offline predictor were built, but the candidate failed the realistic-fill gate. It is paper research only and does not replace the live KAOS Strategy.**

## The strategy

The selected candidate is a fixed small XGBoost model (80 depth-two trees) using 12 causal candle features: body and wick proportions, normalized moving-average/trend context, recent returns, range and volatility. It learns a short-term directional pattern from development data; no OpenAI call, pooled member label, broker account or external execution connection is used.

- Markets: BTC/USDT, ETH/USDT and SOL/USDT on Binance spot. It is not a Pocket Option OTC model.
- Input: completed five-second candles, at least 320 contiguous context bars; reset after a gap.
- BUY when the model's up-score is at least 0.60; SELL when at most 0.40; otherwise HOLD. Scores are not calibrated win probabilities.
- Entry: next observed candle open; 15-second expiration; no overlapping paper positions within an asset.
- Comparison stake: fixed one unit, no martingale or compounding.
- `strategy.py` provides the saved-model predictor; it always reports `executionEnabled: false`, rejects unsupported markets and holds on stale/inadequate context. It does not submit orders. A caller doing paper replay must enforce the position rule.

## Experiment before evaluation

`plan.json` freezes 42 rule/model candidates before examining results. The rules include momentum, trend pullback, breakout, wick rejection, streak fading and a new range-reclaim setup. The range-reclaim rule waits for a prior price stretch outside a 1.5/2-standard-deviation band, then a closed reversal back inside with body confirmation and a weak-trend filter. Three model horizons (15/30/60 seconds) have fixed training parameters and three score thresholds; no hyperparameter fishing follows the final test.

Data: the previously downloaded 357,634 exchange candles from October 1–7, 2026. Gaps/no-trade intervals stay excluded. Indicators warm up inside each segment, so not every input candle becomes a feature row. All markets use the same UTC calendar boundaries:

- Development/model fitting: October 1–3.
- Validation/selection: October 4–5.
- Untouched final replay: October 6–7, evaluated only after writing the selected candidate.

Training labels crossing the development boundary are excluded. There is no random split, no overlapping trade within a market, and no settlement across a gap. Validation requires at least 200 decided trades across two markets and two profitable dates. Selection ranks eligible candidates by Wilson lower confidence bound. Only the selected candidate is evaluated on the final period. The 42-way validation binomial correction is reported; it does not remove correlated-market/day risks.

## Observed results

| Stage/assumption | Wins | Losses | Ties | Win rate excluding ties | P&L at assumed 80% payout |
|---|---:|---:|---:|---:|---:|
| Validation | 652 | 281 | 199 | 69.88% | +240.6 units |
| Final, ideal next open | 769 | 364 | 162 | 67.87% | +251.2 units |
| Final, entry delayed five seconds | 629 | 408 | 155 | 60.66% | +95.2 units |
| Final, entry worsened by 0.01% (one basis point) | 377 | 918 | 0 | 29.11% | -616.4 units |

At 80% assumed payout break-even is 55.56%. Ideal final Wilson 95% lower bound is 65.10%; five-second-delay lower bound is 57.65%. The validation selection-adjusted binomial p-value is approximately 8.56e-18, but only two final dates were observed, three markets are correlated, and most apparent profit came from BTC. SOL had only six decided final trades. Those limitations prevent broad reliability claims regardless of a small conditional p-value.

**The adverse-fill result fails the frozen final gate.** The ideal candle-price edge is too sensitive to a tiny price difference to call it a tradable advantage. Delay and adverse-fill tests are separate stress scenarios, not a combined stress result. Ties assume a refunded stake. Actual binary payouts, broker quotes, spreads, fees, accepted orders and settlement rules are not observed. These results do not establish profitable spot trading either; the P&L uses a hypothetical binary payout, not spot returns.

Source one-second bars can carry previous prices through seconds without trades, which may affect next-open entry assumptions even though all-empty five-second buckets were excluded. The strategy must not be advertised as a 68% live win-rate system or promoted as a pretrained production bot. Training alone does not grant live approval.

## Artifacts and reproduction

`audit/validation.json` contains every candidate. `audit/selection.json` records the frozen choice before final evaluation. `audit/result.json` includes final, delayed and adverse-fill results. `audit/final_trades.csv` contains the selected model's ideal proxy entries/settlements. `audit/selected_model.json` is the saved experimental model, separate from any extension bundle.

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 python scripts/research_crypto_strategy.py --data /private/public-candles-20261001 --out research/crypto_strategy_v1/audit
python -m pytest apps/api/test_crypto_strategy_research.py apps/api/test_broker_edge_research.py apps/api/test_signature_replay.py -q
```

The data directory is the unpacked public ZIP plus its manifest. Runtime uses the API scientific dependencies. `strategy.py` accepts a JSON file with `symbol`, complete `candles`, and epoch-millisecond `asOfMs`. Provide continuous historical context rather than silently truncating/resetting moving-average state each signal.

The next valid research step is new untouched data and forward paper fills using the actual intended broker, with recorded accepted entry/settlement quotes and payouts. Do not tune again on the October 6–7 final period and call the result independent validation. No production files, hosting, payment settings or live trading were changed by this experiment.
