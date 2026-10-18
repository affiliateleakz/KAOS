# KAOS 1.6.56 — Specialist training research

- Classify observed market snapshots at entry time into REVERSAL, RUNNER, BREAKOUT, or unknown. Unknown examples are excluded from specialist training.
- Preserve entry-time classification through independently settled 5/10/15/20/25/30/60-second labels.
- Add KAOS_TRAIN_SPECIALISTS message to train and chronologically validate separate specialist + expiry XGBoost models.
- Require at least 1,000 classified observations per candidate before training request; native trainer independently rejects underpowered or weak holdouts.
- No specialist models are pretrained in this package, no model-selection execution integration, and no verified broker demo trades. This is a research interface, not autonomous trading.
