# KAOS 1.6.50 — Chronological label-overlap safeguard

- Purges training examples whose future outcome interval overlaps the holdout period.
- Rejects duplicate asset/timestamp observations in holdout rather than inflating validation confidence.
- Reports the number of purged observations and uses the correct training count.
- Does not claim 65% profitability or verified Pocket Option demo execution.
