# KAOS 1.6.52 — Multi-expiration native bridge

- Added XGB_TRAIN_MULTI_EXPIRY background request, routing correctly labeled 104-feature observations to the native host train_multi_expiry operation.
- Requires explicit targetHorizonMs (5/10/15/20/25/30/60s), actual completed outcome label, asset and timestamp for each observation.
- Multi-expiry results are audited and returned separately from the single-horizon XGB_MODEL_UPDATE path, preventing accidental replacement of the 30s model.
- Existing 30s training remains unchanged.

**Not complete:** the extension still needs independent real-price settlement/label collection for every expiration, validated model storage and inference routing, and live Pocket Option demo execution tests. This release does not claim 65% accuracy or profitability.
