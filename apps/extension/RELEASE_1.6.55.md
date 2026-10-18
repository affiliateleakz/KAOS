# KAOS 1.6.55 — Reliable multi-expiry sample persistence

- Serializes overlapping sample batches to prevent lost updates.
- Acknowledges samples only after Chrome local storage confirms persistence.
- Rejects inconsistent entry/exit price labels and malformed assets/prices.
- Training waits for queued writes before reading saved examples.
- Keeps a 1,200-record rolling limit for each of seven expirations.
- Does not train specialist models or claim broker-demo validation.
