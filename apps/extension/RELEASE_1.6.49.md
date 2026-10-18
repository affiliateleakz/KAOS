# KAOS 1.6.49 — Holdout model promotion safeguard

- Reject candidate XGBoost models that fail to beat the majority baseline on chronological unseen samples.
- Require >=200 holdout examples and a Wilson 95% lower bound above 50%.
- Preserve prior model when a candidate is rejected; show REJECTED and audit details.
- This is a training reliability fix, not proof of 65% winning trades.
- The pretrained seed remains the earlier weak one-feature model. No multi-expiry models or end-to-end demo execution have been validated.
