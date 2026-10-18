# KAOS 1.6.48 — Full feature native training fix

- Removed the silent 104-to-88 feature truncation in the background native trainer request.
- Native XGBoost now trains and exports 104-feature trees, preserving all available canonical features.
- Added explicit holdout sample count and target horizon in trainer reporting.
- Existing preloaded 1-feature research seed is unchanged; it is **not** evidence of profitable AI.
- This release does NOT include a validated multi-expiry pretrained model, independently validated specialists, or verified autonomous demo execution. A running Chrome/Pocket Option demo session is needed for end-to-end verification.
- Native trainer must be installed on Windows using native_trainer/install_windows.ps1.
