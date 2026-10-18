# KAOS 1.6.45 — AI bootstrap training trigger repair

- On import or restored AI data, schedule native training from valid 104-feature labeled samples.
- Surface native trainer connection errors instead of silently leaving AI in collecting mode.
- Reject invalid/missing sample labels for training requests.
- Surface Chrome storage callback failures.

This does not install the native trainer, fabricate winning trades, or demonstrate a 65% win rate. Demo only.
