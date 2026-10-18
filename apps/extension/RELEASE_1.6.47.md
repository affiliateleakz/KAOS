# KAOS 1.6.47 — Preloaded XGBoost research bootstrap

- Bundles a real historical replay XGBoost model in the extension, loaded automatically on a blank AI installation.
- Restores previously saved user model/samples instead of overwriting them.
- Retains the 1.6.46 native trainer and persistence integration.
- Historical model: 112,258 training examples, 28,079 chronological holdout examples; 49.25% unseen directional accuracy, below 50.70% majority baseline.
- IMPORTANT: This is a populated model, NOT a proven profitable one. The model was built from historical 5s candle replay, uses only feature 0, and targets 30-second direction. Live feature distribution and entry prices may differ.
- AI trust gating remains in place; the seed is NOT authorized to execute live trades.
- To replace the seed with your own model, use AI Lab Import ALL DATA. To reset the AI, use the existing Clear AI action (may trigger bootstrap again on fresh storage).
- Install native trainer separately per native_trainer/README.txt for ongoing training.
