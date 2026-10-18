# KAOS 1.6.54 — Multi-expiration sample retention

- Retains up to 1,200 unique labeled observations per expiry (8,400 total), rather than 4,000 shared.
- Sends the complete collected multi-expiry batch to the native trainer instead of truncating to 1,200 shared observations.
- Reports per-expiry counts when data is insufficient.
- Requires approximately 1,000 examples per expiry for the existing 20% / 200-holdout promotion rule; actual sufficiency also depends on overlap purge and timestamp uniqueness.
- Does not assert a profitable model or verify broker demo execution.
