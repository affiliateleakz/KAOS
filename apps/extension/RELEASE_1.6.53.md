# KAOS 1.6.53 — observed-tick expiration labels

- Captures one 104-feature snapshot per market/5-second interval after existing warmup checks.
- Settles 5/10/15/20/25/30/60-second labels independently using the first observed tick at/after expiry within a 2-second tolerance.
- Excludes missing, late, tied, and invalid observations; these are market-direction labels, NOT broker trade wins.
- Stores up to 4,000 records in extension local storage; exposes `KAOS_EXPIRY_TRAIN_COLLECTED` message for explicitly requested multi-expiration training.
- Does not enable autonomous trades or claim profitable performance.
- Limitations: browser suspension, sparse ticks, timestamp jitter, and delayed execution make this unsuitable as a broker settlement oracle.
