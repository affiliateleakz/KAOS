# KAOS financial AI worker deployment

The KAOS API contains an optional Trading-Hero financial sentiment inference
adapter. The model is **not** automatically installed, started, or validated,
and its output cannot authorize orders.

## Staging
Use an isolated Python worker environment with reviewed pinned versions of
PyTorch, Transformers, Hugging Face Hub and safetensors. Before downloading,
review the model card, upstream file list, license and model-specific terms.
Select an immutable 40-character commit revision.

```shell
python apps/api/provision_trading_hero.py --revision REVIEWED_40_CHARACTER_COMMIT --destination /models/trading-hero
```

After verifying the downloaded snapshot, set the following on the backend
worker (never in the browser extension):

- `KAOS_TRADING_HERO_MODEL_DIR=/models/trading-hero`
- `KAOS_TRADING_HERO_MODEL_VERSION=<reviewed-model-revision>`
- `KAOS_COLLECTOR_KEY=<unique-secret>`

Smoke-test `kaos_financial_inference.classify_headlines` with known financial
headlines and review its labels before connecting authenticated collectors to
`POST /api/v1/intelligence/ingest/classify-headlines`.

The collector must gather attributed publication URLs, timestamps, and source
content; model scoring alone does not prove a headline is accurate or timely.
Measure inference latency, failure rates, and chronological holdout quality.
The live order path remains disabled until separate broker, data, risk and
paper-trading validation completes.

FinGPT, AlphaFin Stage 1/2 and TigerTrading still require separately
reviewed model-specific workers. Their presence in the model registry does
not imply functioning inference.
