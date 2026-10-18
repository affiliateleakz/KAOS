# KAOS 1.6.43 — strategy integrity fixes

- Evaluate S/R on completed 5s, 15s, 30s and 60s candles, not partial higher-timeframe bars.
- Use the most recent 20 completed 30s candles for S/R.
- Require enough 60s candles for the 21-period trend context.
- Enforce one strategy evaluation per completed 5s bar per asset.
- Do not fall through to the legacy micro strategy while S/R is warming up.

**Not a proven profitable strategy.** This build does not include a pretrained extension-native XGBoost/LightGBM model or autonomous AI training repair. Keep on demo until independently validated. The signal confidence numbers in the legacy strategy are heuristic, not calibrated win probabilities.
