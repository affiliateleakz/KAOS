# Continuous KAOS learning

## Membership and model access

Pro includes a private model that starts untrained and learns from that member’s eligible observations. Ultimate adds access to owner-published shared pretrained models when available. A membership purchase does not manufacture a trained model. Super administrators also have a separate owner model trained from the service pool. Personal models and their weights remain scoped to their owner; Pro cannot download the shared pretrained bundle.

Learning is a required, disclosed service practice, not an opt-in. Registration, sign-in, the member portal and privacy notice explain it. The telemetry endpoint ignores old local consent toggles. Account deletion removes linked samples and training jobs and retires linked models. No existing account records were migrated by preparing this change.

Only whitelisted numerical price/technical features and settled trade labels enter binary training. Names, email, credentials, balances, payment information, free text and screenshots are excluded. A private pseudonymous account link supports access control and deletion; this is not a claim of irreversible anonymity. Observations expire after 90 days. Store listing disclosures must accurately describe this collection before resubmission.

## What runs and what remains unvalidated

Passenger accepts minimized observations and queues jobs; it does not fit models. The separate worker rotates stock, crypto and forex research, captures existing news/market/disclosure evidence and updates bounded research candidates. This path does not call OpenAI. Options remain research candidates rather than a trained options execution model.

Binary bot learning is separate from slower multi-asset research. Its first supported schema is `kaos-binary-104-v1`: Pocket Option, canonical five-second feature vectors, with separate account mode and expiry scopes. The default scope is `pocket_option:binary:5s:20s:real`. Different brokers, expiries and demo/real data are not silently pooled into one execution model. Member-reported settlements are not represented as broker-verified trades. Unknown account mode, malformed vectors and inconsistent outcomes are rejected. Context features without reliable historical provenance are masked.

A fit requires at least 500 eligible observations, chronological train/holdout separation with label purging, sufficient class coverage, at least 100 actionable holdout predictions and conservative statistical gates. Repeated observations of the same market/time are deduplicated. A candidate must then pass at least 100 later actionable observations collected after its training window. Shared training also requires three current contributors. Passing these gates creates a research artifact, not permission for live trading. Published bundles expire after 30 days. Private and owner candidates also need prospective validation before download.

No pretrained model has been published by this implementation. The old unverified bootstrap was removed from the distributed extension and archived under `research/legacy_bootstrap`. Bundles are authenticated, account-scoped, advisory and explicitly marked `executionEnabled: false`. Existing live execution gates remain separate.

## Worker hosting: prepared, not started

The owner has not selected hosting. Do not run this worker inside shared cPanel Passenger. A suitable host needs network access to the same MongoDB and configured research providers. Keep database access private/TLS where supported. Use the same private provider vault key (`KAOS_COMMERCE_VAULT_KEY`) or securely provision its key file; do not copy credentials into Git or a browser bundle.

Two deployment templates are supplied:

- `deploy/training/kaos-training.service` for a dedicated Linux user, checkout at `/opt/KAOS`, Python virtual environment and private `/etc/kaos/training.env`.
- The opt-in Docker Compose `training` profile, with one CPU, 1 GB memory and no published HTTP port. It is excluded from the default web stack.

Copy `deploy/training/training.env.example` privately and supply the existing database, JWT and provider settings. `KAOS_TRAINING_WORKER_ENABLED=true` is required explicitly. The default interval is 300 seconds; numerical libraries use one thread. Starting either template is a later hosting action, not something the website automatically does. Use one scheduled worker; MongoDB leases prevent concurrent cycle ownership. The admin AI center shows heartbeat, errors, queued owner training and model validation/publishing status. Missing heartbeat means stopped; do not interpret it as successful background learning.

## IPOs and ICOs

Radar includes IPOs & ICOs. The IPO calendar uses the existing server-side Alpha Vantage key and shared request budget/cache. Missing credentials or provider failures display an honest empty/setup state. ICO entries require an owner-provided dated HTTPS source and explicit publication; no synthetic offerings are generated. Calendar entries are informational, not a token sale or an order endpoint.

## Verification and strategy evidence

API tests cover mandatory ingestion, private/shared access, revoked devices, chronological fitting, future validation, queue ownership and offering validation. Browser fixtures exercise Pro training, worker-not-running state and the IPO/ICO screens. These fixtures do not certify provider availability, Google Cloud configuration or live broker execution.

See `research/signature_sr11/README.md` for the exact current strategy replay and its insufficient holdout evidence. Genuine broker history is still needed for broker-specific evaluation.
