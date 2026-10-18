# KAOS Trading Bot 1.6.37

## Verified before modification
LightGBM was already present in the 1.6.36 engine:
- native model fields `lightgbmGlobal` and `lightgbmAssetModels`
- independent LightGBM shadow prediction path
- holdout/validation metrics
- XGBoost-vs-LightGBM champion selection

A stale legacy comment still said LightGBM had been removed; the functioning code below
that comment contradicted it. This release does not duplicate LightGBM.

## Added
- LightGBM is now a first-class card in KAOS AI Intelligence.
- XGBoost and LightGBM predictions are exposed independently to the UI.
- OPENAI BRAIN card and secure KAOS-server client boundary.
- Server contract for `/api/v1/ai/brain`.
- OpenAI API key is never stored in the extension.
- OpenAI remains shadow-only until the server endpoint is implemented and authenticated.
- Existing Pocket Option AI observer and External Signal AI slot retained.
- Existing trading authority/execution logic unchanged.
