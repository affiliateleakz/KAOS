# KAOS Trading Engine 2.0.2 — FinBERT shadow module

- New `kaos_finbert.py` with lazy local-only ProsusAI/finbert model loading, timestamp safeguards, normalized sentiment, deterministic event IDs.
- New `routes_finbert.py`: authenticated paid-member status and analyze endpoints, Mongo shadow event persistence, no execution rights.
- Registered router in `server.py`.
- `test_kaos_finbert.py` provides six offline unit tests using a stub predictor; **does not test actual model inference or live data feeds**.
- Dependencies not automatically installed: deployment must separately provision compatible `transformers`, `torch`, and a locally cached approved FinBERT model. Configure `KAOS_FINBERT_MODEL_PATH` and `KAOS_FINBERT_ENABLED=enabled` only after provisioning. Default is disabled.
- Input headlines must be provided by an upstream licensed news source. No automated news ingestion, asset relevance ranking, or backtesting is included.
- FinBERT is strictly SHADOW_ONLY. Does not modify broker orders, live strategy decisions, or risk controls.
- Do not deploy ZIP over live Asura backend without staging, secret review, and regression testing.
