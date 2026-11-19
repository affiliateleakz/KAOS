# KAOS AI financial model worker: deployment boundary

**Not automatically deployed or trading-enabled.** The API adapter uses local
Trading-Hero weights; API startup never pulls remote models. Install the worker
in a separate container/virtual environment with pinned, audited versions of
`torch`, `transformers`, `huggingface_hub`, `safetensors`. Review model
licenses and downloaded artifacts before enabling the worker.

1. On an isolated host, select and inspect a specific immutable model revision.
2. Run `python apps/api/provision_financial_model.py --model trading_hero --revision <reviewed-40-character-hash> --destination /models/trading_hero`.
3. Set `KAOS_TRADING_HERO_MODEL_DIR=/models/trading_hero`,
   `KAOS_TRADING_HERO_MODEL_VERSION=<reviewed-revision>`, and a collector-only
   `KAOS_COLLECTOR_KEY` in the **server runtime**, never the extension.
4. Smoke test `kaos_financial_inference.classify_headlines` on known examples.
   Verify label mappings for the downloaded revision before trusting scores.
5. Configure a separately authenticated news collector to call
   `POST /api/v1/intelligence/ingest/classify-headlines`; it must attach real
   attributed URLs and publication timestamps. Keep HTTPS and network
   restrictions between the collector and API.
6. Assess accuracy on chronological market-news validation data, verify
   deduplication, availability, costs, and observe paper-trading outcomes.

FinGPT, TigerTrading, AlphaFin Stage 1/2, and StockGPT numerical research
remain **not provisioned**; model registration alone is not an inference service.
The collected sentiment is research context, not direct BUY/SELL trading
authority. No API endpoint added here submits orders.
